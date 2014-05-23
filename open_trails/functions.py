from open_trails import app
from werkzeug.utils import secure_filename
import os, os.path, json, subprocess, zipfile, csv, boto, tempfile
from boto.s3.key import Key

def clean_name(name):
    '''
    Replace underscores with dashes in an steward_name for prettier urls
    '''
    return secure_filename(name).lower().replace("_","-")

class FilesystemDatastore:

    def __init__(self, dirpath):
        self.dirpath = dirpath

    def upload(self, filepath):
        ''' Upload a file to the datastore.
        '''
        destination = os.path.join(self.dirpath, filepath)
        print 'uploading', filepath, 'to', destination
        try:
            os.makedirs(os.path.dirname(destination))
        except OSError:
            pass
        with open(filepath, 'r') as input:
            # filepath example: "steward/uploads/file.csv"
            with open(destination, 'w') as output:
                output.write(input.read())

    def download(self, filepath):
        ''' Download a single file from datastore to local working directory.
        '''
        with open(os.path.join(self.dirpath, filepath), 'r') as input:
            with open(filepath, 'w') as output:
                output.write(input.read())
    
    def filelist(self, prefix):
        ''' Retrieve a list of files under a name prefix.
        '''
        names = []

        for dirname, dirnames, filenames in os.walk(self.dirpath):
            # print path to all filenames.
            for filename in filenames:
                name = os.path.relpath(os.path.join(dirname, filename), self.dirpath)
                if name.startswith(prefix):
                    names.append(name)

        return names

def make_datastore(config):
    ''' Returns an object with an upload method.
    '''
    from urlparse import urlparse
    scheme, host, path, _, _, _ = urlparse(config)

    if scheme == 'file':
      # make a filesystem datastore suitable for testing
      return FilesystemDatastore(path)

    else:
      # make a new boto-based S3 thing
      raise NotImplementedError("Don't know how to do anything with %s yet" % config)

def upload_to_s3(filepath, datastore):
    '''
    Upload a file to S3
    Return url to file
    '''
    raise NotImplementedError('making this go away')
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
