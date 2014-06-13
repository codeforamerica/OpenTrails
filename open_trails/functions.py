from open_trails import app
from werkzeug.utils import secure_filename
import os, os.path, json, subprocess, zipfile, csv, boto, tempfile, urlparse, urllib, zipfile
from boto.s3.key import Key
from models import Steward


def make_steward_from_datastore(datastore, filepath):
    '''
    Creates a steward object from the stewards.csv file
    '''
    datastore.download(filepath)
    with open(filepath, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            steward = Steward(row['id'], row['url'], row['name'], row['phone'], row['address'], row['publisher'])
            return steward


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

