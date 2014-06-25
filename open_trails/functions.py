from open_trails import app
from werkzeug.utils import secure_filename
import os, os.path, json, subprocess, zipfile, csv, boto, tempfile, urlparse, urllib, zipfile
from boto.s3.key import Key
from models import Dataset
from flask import make_response


def get_dataset(datastore, id):
    '''
    Creates a dataset object from the .valid file
    '''
    try:
        datastore.download(id + '/uploads/.valid')
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


def unzip(filepath):
    '''Unzip and return the path of a shapefile
    '''
    zf = zipfile.ZipFile(filepath, 'r')
    zf.extractall(os.path.split(filepath)[0])
    for file in os.listdir(os.path.split(filepath)[0]):
        if '.shp' in file:
            return os.path.split(filepath)[0] + '/' + file

def compress(input, output):
    '''Zips up a file
    '''
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as myzip:
        myzip.write(input, os.path.split(input)[1])

def get_sample_of_original_segments(steward):
    # Download the original segments file
    filelist = steward.datastore.filelist(steward.id)
    for file in filelist:
        if "/uploads" in file and ".geojson.zip" in file:
            segments_zip = file

    steward.datastore.download(segments_zip)

    # Unzip it
    zf = zipfile.ZipFile(segments_zip, 'r')
    zf.extractall(os.path.split(segments_zip)[0])

    # Find geojson file
    for file in os.listdir(steward.id + "/uploads/"):
        if file.endswith(".geojson"):
            segmentsfile = open(steward.id + "/uploads/" + file)
            original_segments = json.load(segmentsfile)
            segmentsfile.close()
            sample_segment = {'type': 'FeatureCollection', 'features': []}
            sample_segment['features'].append(original_segments['features'][0])

    return sample_segment

