from open_trails import app
import urlparse, os, urllib, boto, glob
from boto.s3.key import Key

class Steward:

    def __init__(self, initial_data):
        '''
        Basic info about a steward
        '''
        # self.id = id
        # self.name = name
        # self.url = url
        # self.phone = phone
        # self.address = address
        # self.publisher = publisher
        # self.datastore = datastore
        self.datastore = None
        self.status = None
        
        for key in initial_data:
            setattr(self, key, initial_data[key])
        

    def get_status(self):
        '''
        Use the filelist from datastore to figure out how far along
        this steward is in the process.
        '''

        filelist = self.datastore.filelist(self.id)
        # matching = [filename for filename in filelist if ".geojson.zip" in filename]

        if not any(".geojson.zip" in filename for filename in filelist): 
            self.status = "needs segments"

        # If the original segments file has been uploaded
        # But the transformed segments arent there
        if any(".geojson.zip" in filename for filename in filelist):
            if not "/opentrails/segments.geojson.zip" in filelist:
                self.status = "show uploaded segments"

        elif any("segments.geojson.zip" in filename for filename in filelist):
            self.status = "show segments"

class FilesystemDatastore:

    def __init__(self, dirpath):
        self.dirpath = dirpath

    def upload(self, filepath):
        ''' Upload a file to the datastore.
        '''
        destination = os.path.join(self.dirpath, filepath)
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
        # Check if file already exists
        if not os.path.isfile(filepath):
            with open(os.path.join(self.dirpath, filepath), 'r') as input:
                with open(filepath, 'w') as output:
                    output.write(input.read())

    def filelist(self, prefix):
        ''' Retrieve a list of files under a name prefix.
        '''
        names = []

        for dirname, dirnames, filenames in os.walk(self.dirpath):
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
        # Check if file already exists
        if not os.path.isfile(filepath):
            key = self.bucket.get_key(filepath)
            try:
                os.makedirs(os.path.dirname(filepath))
            except OSError:
                pass
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
