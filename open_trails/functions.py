from open_trails import app
from werkzeug.utils import secure_filename
from itertools import groupby, count
from operator import itemgetter
from StringIO import StringIO
import os, os.path, json, subprocess, zipfile, csv, boto, tempfile, urlparse, urllib, zipfile

from boto.s3.key import Key
from models import Dataset
from flask import make_response

def get_dataset(datastore, id):
    '''
    Creates a dataset object from the .valid file
    '''
    try:
        upload_dir = os.path.join(id, 'uploads')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        valid_path = os.path.join(upload_dir, '.valid')
        datastore.download(valid_path)
    except AttributeError:
        return None
    with open(id + '/uploads/.valid', 'r') as validfile:
        if validfile.read() == id:
            dataset = Dataset(id)
            dataset.datastore = datastore
            return dataset


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in set(['zip'])

def clean_name(name):
    '''
    Replace underscores with dashes in an steward_name for prettier urls
    '''
    return secure_filename(name).lower().replace("_","-")

def make_id_from_url(url):
    ''' Clean up the url given to make a steward id
    '''
    parsed = urlparse.urlparse(url)
    steward_id = parsed.netloc.split('.')[0]
    return secure_filename(steward_id).lower().replace("_","-")


def unzip(zipfile_path, search_ext='.shp', other_exts=('.dbf', '.prj', '.shx')):
    ''' Unzip and return the path of a shapefile.
    '''
    zf = zipfile.ZipFile(zipfile_path, 'r')
    dirname = os.path.dirname(zipfile_path)
    shapefile_path = None
    
    for name in sorted(zf.namelist()):
        base, (_, ext) = os.path.basename(name), os.path.splitext(name)
        
        if base.startswith('.'):
            continue
        
        if ext in [search_ext] + list(other_exts):
            unzipped_path = os.path.join(dirname, base)
            
            with open(unzipped_path, 'w') as f:
                f.write(zf.open(name).read())
            
            if ext == search_ext:
                shapefile_path = unzipped_path
    
    return shapefile_path

def compress(input, output):
    '''Zips up a file
    '''
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as myzip:
        myzip.write(input, os.path.split(input)[1])

def get_sample_of_original_segments(dataset):
    # Download the original segments file
    segments_zip = dataset.id + '/uploads/trail-segments.geojson.zip'
    dataset.datastore.download(segments_zip)

    # Unzip it
    zf = zipfile.ZipFile(segments_zip, 'r')
    zf.extractall(os.path.split(segments_zip)[0])

    # Find geojson file
    for file in os.listdir(dataset.id + "/uploads/"):
        if file.endswith(".geojson"):
            segmentsfile = open(dataset.id + "/uploads/" + file)
            original_segments = json.load(segmentsfile)
            segmentsfile.close()
            sample_segment = {'type': 'FeatureCollection', 'features': []}
            sample_segment['features'].append(original_segments['features'][0])

    return sample_segment

def get_sample_uploaded_features(dataset, zipped_geojson_name):
    # Download the original segments file
    upload_dir = os.path.join(dataset.id, 'uploads')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    segments_zip = os.path.join(upload_dir, zipped_geojson_name)
    dataset.datastore.download(segments_zip)

    # Unzip it
    zf = zipfile.ZipFile(segments_zip, 'r')
    zf.extractall(os.path.split(segments_zip)[0])

    # Find geojson file
    for file in os.listdir(dataset.id + "/uploads/"):
        if file.endswith(".geojson"):
            segmentsfile = open(dataset.id + "/uploads/" + file)
            original_segments = json.load(segmentsfile)
            segmentsfile.close()
            return original_segments['features'][:3]

    return []

def get_sample_segment_features(dataset):
    return get_sample_uploaded_features(dataset, 'trail-segments.geojson.zip')

def get_sample_trailhead_features(dataset):
    return get_sample_uploaded_features(dataset, 'trail-trailheads.geojson.zip')

def encode_list(items):
    '''
    '''
    return '; '.join(map(str, items))

def make_name_trails(segment_features):
    '''
    '''
    names = [(f['properties']['name'], f['properties']['id'])
             for f in segment_features
             if f['properties']['name']]
    
    # Cut to the chase if there's no name.
    if not names:
        return []
    
    # Generate a list of (name, ids) tuples
    groups = groupby(names, itemgetter(0))
    name_ids = [(name, encode_list(map(itemgetter(1), names_ids)))
                for (name, names_ids) in groups]
    
    id_counter = count(1)

    return [dict(id=str(id_counter.next()),
                 name=name, segment_ids=ids,
                 description=None, part_of=None)
            for (name, ids) in name_ids]

def package_opentrails_archive(dataset):
    '''
    '''
    buffer = StringIO()
    zf = zipfile.ZipFile(buffer, 'w')
    
    # Download the transformed segments and trailheads files
    opentrails_dir = os.path.join(dataset.id, 'opentrails')
    if not os.path.exists(opentrails_dir):
        os.makedirs(opentrails_dir)

    transformed_segments_zip = os.path.join(opentrails_dir, 'segments.geojson.zip')
    transformed_trailheads_zip = os.path.join(opentrails_dir, 'trailheads.geojson.zip')
    dataset.datastore.download(transformed_segments_zip)
    # We moved this up from below the unzip and re-zip section
    # If a user skips adding and converting trailheads, we want to give them the option
    # to download a zip of their data thus far.
    try:
        dataset.datastore.download(transformed_trailheads_zip)
        trailheads_path = unzip(transformed_trailheads_zip, '.geojson', [])
        zf.write(trailheads_path, 'trailheads.geojson')
    except AttributeError:
        pass

    # Unzip it and re-zip them.
    segments_path = unzip(transformed_segments_zip, '.geojson', [])
    zf.write(segments_path, 'trail_segments.geojson')

    # Download the named trails file
    named_trails_path = os.path.join(opentrails_dir, 'named_trails.csv')
    dataset.datastore.download(named_trails_path)
    zf.write(named_trails_path, 'named_trails.csv')
    
    # Download the stewards file
    stewards_path = os.path.join(opentrails_dir, 'stewards.csv')
    dataset.datastore.download(stewards_path)
    zf.write(stewards_path, 'stewards.csv')
    
    zf.close()
    buffer.seek(0)
    
    return buffer
