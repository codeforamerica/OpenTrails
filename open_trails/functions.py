from open_trails import app
from werkzeug.utils import secure_filename
import os, os.path, json, subprocess, zipfile, csv, boto, tempfile, urlparse, urllib
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
    
    def stewards(self):
        ''' Retrieve a list of stewards based on directory names.
        '''
        return list(os.listdir(self.dirpath))

class S3Datastore:

    def __init__(self, key, secret, bucketname):
        conn = boto.connect_s3(key, secret)
        self.bucket = conn.get_bucket(bucketname)
    
    #def __delete__(self):
    #    self.conn.close()

    def upload(self, filepath):
        ''' Upload a file to S3.
        '''
        k = Key(self.bucket)
        k.key = filepath
        k.set_contents_from_filename(filepath)
        self.bucket.set_acl('public-read', k.key)

    def download(self, filepath):
        ''' Download a single file from S3 to local working directory.
        '''
        key = self.bucket.get_key(filepath)
        key.get_contents_to_filename(filepath)
    
    def filelist(self, prefix):
        ''' Retrieve a list of files under a name prefix.
        '''
        return [file.name for file in self.bucket.list(prefix)]
    
    def stewards(self):
        ''' Retrieve a list of stewards based on directory names.
        '''
        return [steward.name.replace('/', '') for steward in self.bucket.list('', '/')]

def make_datastore(config):
    ''' Returns an object with an upload method.
    '''
    parsed = urlparse.urlparse(config)

    if parsed.scheme == 'file':
      # make a filesystem datastore suitable for testing
      return FilesystemDatastore(parsed.path)
    
    elif parsed.scheme == 's3n':
      # make an S3 datastore using a Hadoop-style URL.
      key, secret = urllib.unquote(parsed.username), urllib.unquote(parsed.password)
      return S3Datastore(key, secret, parsed.hostname)

    else:
      # make a new boto-based S3 thing
      raise NotImplementedError("Don't know how to do anything with %s yet" % config)

def unzip(filepath):
    '''Unzip and return the path of a shapefile
    '''
    zf = zipfile.ZipFile(filepath, 'r')
    zf.extractall(os.path.split(filepath)[0])
    for file in os.listdir(os.path.split(filepath)[0]):
        if '.shp' in file:
            return os.path.split(filepath)[0] + '/' + file
