from open_trails import app
import urlparse, os, urllib, boto, glob
from StringIO import StringIO
from boto.s3.key import Key

class Dataset:

    def __init__(self, id):
        '''
        Basic info about a dataset
        '''
        self.id = id
        # self.name = name
        # self.url = url
        # self.phone = phone
        # self.address = address
        # self.publisher = publisher
        # self.datastore = datastore
        self.datastore = None
        # self.status = None
        
        # for key in initial_data:
        #     setattr(self, key, initial_data[key])

class FilesystemDatastore:

    def __init__(self, dirpath):
        self.dirpath = dirpath

    def write(self, filepath, buffer):
        ''' Write a buffer for a single file.
        '''
        destination = os.path.join(self.dirpath, filepath)

        try:
            os.makedirs(os.path.dirname(destination))
        except OSError:
            pass
        finally:
            with open(destination, 'w') as output:
                output.write(buffer.getvalue())
    
    def read(self, filepath):
        ''' Return a buffer for a single file.
        '''
        with open(os.path.join(self.dirpath, filepath), 'r') as input:
            return StringIO(input.read())
    
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

    def datasets(self):
        ''' Retrieve a list of datasets based on directory names.
        '''
        return list(os.listdir(self.dirpath))

class S3Datastore:

    def __init__(self, key, secret, bucketname):
        conn = boto.connect_s3(key, secret)
        self.bucket = conn.get_bucket(bucketname)

    #def __delete__(self):
    #    self.conn.close()

    def write(self, filepath, buffer):
        ''' Write a buffer for a single file.
        '''
        k = Key(self.bucket)
        k.key = filepath
        k.set_contents_from_string(buffer.getvalue())
        self.bucket.set_acl('public-read', k.key)
    
    def read(self, filepath):
        ''' Return a buffer for a single file.
        '''
        key = self.bucket.get_key(filepath)
        return StringIO(key.get_contents_as_string())
    
    def filelist(self, prefix):
        ''' Retrieve a list of files under a name prefix.
        '''
        return [file.name for file in self.bucket.list(prefix)]

    def datasets(self):
        ''' Retrieve a list of datasets based on directory names.
        '''
        return [dataset.name.replace('/', '') for dataset in self.bucket.list('', '/')]

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
