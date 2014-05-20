from open_trails import app
from werkzeug.utils import secure_filename
import os, json, subprocess, zipfile, csv, boto
from boto.s3.key import Key

def clean_name(name):
    '''
    Replace underscores with dashes in an steward_name for prettier urls
    '''
    return secure_filename(name).lower().replace("_","-")

def upload_to_s3(filepath):
    '''
    Upload a file to S3
    Return url to file
    '''
    conn = boto.connect_s3(app.config["AWS_ACCESS_KEY_ID"], app.config["AWS_SECRET_ACCESS_KEY"])
    bucket = conn.get_bucket(app.config["S3_BUCKET_NAME"])
    k = Key(bucket)
    k.key = filepath
    k.set_contents_from_filename(filepath)
    bucket.set_acl('public-read', k.key)
    conn.close()
    # return "https://%s.s3.amazonaws.com/%s" % (app.config["S3_BUCKET_NAME"], filepath

def download_from_s3(filepath):
    '''Download a file from s3 and save it to the same path.
    '''
    conn = boto.connect_s3(app.config["AWS_ACCESS_KEY_ID"], app.config["AWS_SECRET_ACCESS_KEY"])
    bucket = conn.get_bucket(app.config["S3_BUCKET_NAME"])
    key = bucket.get_key(filepath)
    key.get_contents_to_filename(filepath)
    conn.close()

def make_folders(steward_name):
    '''Try and make the folders, ex. san-antonio/uploads, san-antonio/opentrails
    '''
    try:
        os.mkdir(steward_name)
    except OSError:
        pass
    try:
        os.mkdir(os.path.join(steward_name, 'uploads'))
    except OSError:
        pass
    try:
        os.mkdir(os.path.join(steward_name, 'opentrails'))
    except OSError:
        pass

def get_stewards_list():
    '''Return a list of stewards from S3 folder names
    '''
    conn = boto.connect_s3(app.config["AWS_ACCESS_KEY_ID"], app.config["AWS_SECRET_ACCESS_KEY"])
    bucket = conn.get_bucket(app.config["S3_BUCKET_NAME"])
    conn.close()
    stewards_list = []
    for steward in list(bucket.list("", "/")):
        stewards_list.append(steward.name.replace("/",""))
    return stewards_list

def get_s3_filelist(steward_name):
    '''Return a list of files saved in a named S3 folder.
    '''
    conn = boto.connect_s3(app.config["AWS_ACCESS_KEY_ID"], app.config["AWS_SECRET_ACCESS_KEY"])
    bucket = conn.get_bucket(app.config["S3_BUCKET_NAME"])
    conn.close()
    filelist = []
    for file in list(bucket.list(steward_name)):
        filelist.append(file.name)
    return filelist

def unzip(filepath):
    '''Unzip and return the path of a shapefile
    '''
    zf = zipfile.ZipFile(filepath, 'r')
    zf.extractall(os.path.split(filepath)[0])
    for file in os.listdir(os.path.split(filepath)[0]):
        if '.shp' in file:
            return os.path.split(filepath)[0] + '/' + file
