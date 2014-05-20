from open_trails import app
from werkzeug.utils import secure_filename
import os, json, subprocess, zipfile, csv, boto
from boto.s3.key import Key

# ALLOWED_EXTENSIONS = set(['zip'])
#
# def allowed_file(filename):
#     return '.' in filename and \
#            filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def clean_name(name):
    '''
    Replace underscores with dashes in an org_name for prettier urls
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
    conn = boto.connect_s3(app.config["AWS_ACCESS_KEY_ID"], app.config["AWS_SECRET_ACCESS_KEY"])
    bucket = conn.get_bucket(app.config["S3_BUCKET_NAME"])
    key = bucket.get_key(filepath)
    key.get_contents_to_filename(filepath)
    conn.close()

# def unzipfile(filepath):
#     # Unzips an archive and searches for the contained .shp file
#     # Returns the path to that .shp file
#     zf = zipfile.ZipFile(filepath, 'r')
#     zf.extractall(app.config['UPLOAD_FOLDER'])
#     for name in zf.namelist():
#         if name.rsplit('.', 1)[1] == 'shp':
#             return name

def make_folders(org_name):
    # Try and make the folder, ex. san-antonio/uploads, san-antonio/opentrails
    try:
        os.mkdir(org_name)
    except OSError:
        pass
    try:
        os.mkdir(os.path.join(org_name, 'uploads'))
    except OSError:
        pass
    try:
        os.mkdir(os.path.join(org_name, 'opentrails'))
    except OSError:
        pass

def get_orgs_list():
    conn = boto.connect_s3(app.config["AWS_ACCESS_KEY_ID"], app.config["AWS_SECRET_ACCESS_KEY"])
    bucket = conn.get_bucket(app.config["S3_BUCKET_NAME"])
    conn.close()
    orgs_list = []
    for org in list(bucket.list("", "/")):
        orgs_list.append(org.name.replace("/",""))
    return orgs_list
