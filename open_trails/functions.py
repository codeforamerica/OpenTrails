from open_trails import app
from werkzeug.utils import secure_filename
from itertools import groupby, count
from operator import itemgetter
from StringIO import StringIO
from tempfile import mkdtemp
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
        valid_file = datastore.read(valid_path)
    except AttributeError:
        return None
    
    if valid_file.read() == id:
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
    ''' Unzip and return the path of a shapefile in a temp directory.
    '''
    zf = zipfile.ZipFile(zipfile_path, 'r')
    dirname = mkdtemp(prefix='unzip-', suffix=search_ext)
    foundfile_path = None
    
    for name in sorted(zf.namelist()):
        base, (_, ext) = os.path.basename(name), os.path.splitext(name)
        
        if base.startswith('.'):
            continue
        
        if ext in [search_ext] + list(other_exts):
            unzipped_path = os.path.join(dirname, base)
            
            with open(unzipped_path, 'w') as f:
                f.write(zf.open(name).read())
            
            if ext == search_ext:
                foundfile_path = unzipped_path
    
    return foundfile_path

def compress(input, output):
    '''Zips up a file
    '''
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as myzip:
        myzip.write(input, os.path.split(input)[1])

def get_sample_uploaded_features(dataset, zipped_geojson_name):
    '''
    '''
    zip_path = os.path.join(dataset.id, 'uploads', zipped_geojson_name)
    zip_buffer = dataset.datastore.read(zip_path)
    zf = zipfile.ZipFile(zip_buffer, 'r')
    
    # Search for a .geojson file
    for name in zf.namelist():
        _, ext = os.path.splitext(name)
        
        if ext == '.geojson':
            # Return its first three features
            gf = zf.open(name, 'r')
            geojson = json.load(gf)
            return geojson['features'][:3]

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
    ot_prefix = os.path.join(dataset.id, 'opentrails')

    # We moved this up from below the unzip and re-zip section
    # If a user skips adding and converting trailheads, we want to give them the option
    # to download a zip of their data thus far.
    try:
        trailheads_zipname = os.path.join(ot_prefix, 'trailheads.geojson.zip')
        trailheads_zipfile = dataset.datastore.read(trailheads_zipname)
        trailheads_path = unzip(trailheads_zipfile, '.geojson', [])
        zf.writestr('trailheads.geojson', open(trailheads_path).read())
    except AttributeError:
        pass

    # Add the segments file
    segments_zipname = os.path.join(ot_prefix, 'segments.geojson.zip')
    segments_zipfile = dataset.datastore.read(segments_zipname)
    segments_path = unzip(segments_zipfile, '.geojson', [])
    zf.writestr('trail_segments.geojson', open(segments_path).read())

    # Add the named trails file
    named_trails_path = os.path.join(ot_prefix, 'named_trails.csv')
    named_trails_data = dataset.datastore.read(named_trails_path)
    zf.writestr('named_trails.csv', named_trails_data.read())
    
    # Add the stewards file
    stewards_path = os.path.join(ot_prefix, 'stewards.csv')
    stewards_data = dataset.datastore.read(stewards_path)
    zf.writestr('stewards.csv', stewards_data.read())
    
    zf.close()
    buffer.seek(0)
    
    return buffer
