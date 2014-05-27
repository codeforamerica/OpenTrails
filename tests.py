# -- coding: utf-8 --
from shutil import rmtree, copy
from unittest import TestCase, main
from os.path import join, dirname
import os, glob
from urlparse import urljoin
from tempfile import mkdtemp
from bs4 import BeautifulSoup

from open_trails import app, transformers
from open_trails.functions import unzip

class FakeUpload:
    ''' Pretend to be a file upload in flask.
    '''
    def __init__(self, path):
        self._file = open(path, 'r')
        self.filename = path

    def save(self, path):
        with open(path, 'w') as file:
            file.write(self._file.read())

class TestTransformers (TestCase):

    def setUp(self):
        self.dir = os.getcwd()
        self.tmp = mkdtemp(prefix='plats-')
        names = ('test-files/lake-man.zip',
                 'test-files/lake-man-GGNRA.zip',
                 'test-files/lake-man-San-Antonio.zip',
                 'test-files/lake-man-Santa-Clara.zip',
                 'test-files/lake-man-Portland.zip')
        for name in names:
            copy(name, self.tmp)

    def tearDown(self):
        rmtree(self.tmp)

    def testConvert(self):
        ''' Test basic SHP to GeoJSON conversion.
        '''
        for name in os.listdir(self.tmp):
            path = unzip(join(self.tmp,name))
            self.doFileConversion(path)

    def doFileConversion(self, path):
        ''' Test conversion results for named file.
        '''
        geojson = transformers.transform_shapefile(path)

        #
        # Is it GeoJSON?
        #
        self.assertEqual(geojson['type'], 'FeatureCollection')
        self.assertEqual(len(geojson['features']), 6)
        self.assertEqual(set([f['geometry']['type'] for f in geojson['features']]), set(['LineString']))

        #
        # Does it cover the expected geographic area?
        #
        lons, lats = [], []

        for f in geojson['features']:
            lons.extend([x for (x, y) in f['geometry']['coordinates']])
            lats.extend([y for (x, y) in f['geometry']['coordinates']])

        self.assertTrue(37.80071 < min(lats) and max(lats) < 37.80436)
        self.assertTrue(-122.25925 < min(lons) and max(lons) < -122.25671)

class TestApp (TestCase):

    def setUp(self):
        self.dir = os.getcwd()
        self.tmp = mkdtemp(prefix='plats-')
        names = ('test-files/lake-man.zip',
                 'test-files/lake-man-GGNRA.zip',
                 'test-files/lake-man-San-Antonio.zip',
                 'test-files/lake-man-Santa-Clara.zip',
                 'test-files/lake-man-Portland.zip')
        for name in names:
            copy(name, self.tmp)

        os.mkdir(self.tmp + '/working-dir')
        os.chdir(self.tmp + '/working-dir')

        os.mkdir(self.tmp + '/datastore')
        app.config.update(DATASTORE='file://%s/datastore' % self.tmp)

        self.app = app.test_client()

    def tearDown(self):
        rmtree(self.tmp)
        os.chdir(self.dir)

    def test_new_steward(self):
        '''Test creating a new stewards.csv
        '''
        data = {
            "name" : "Test Steward",
            "email" : "testemail@email.com",
            "url" : "http://testurl.com",
            "phone" : "123456789"
            }

        created = self.app.post('/new-steward', data=data, follow_redirects=True)
        self.assertEqual(created.status_code, 200)
        self.assertTrue('test-steward' in created.data)

    def test_stewards_list(self):
        ''' Test that /stewards returns a list of stewards
        '''
        for i in range(1,10):
            data = {
                "name" : "Test Steward" + str(i),
                "email" : "testemail@email.com",
                "url" : "http://testurl.com",
                "phone" : "123456789"
                }
            self.app.post('/new-steward', data=data)

        response = self.app.get('/stewards')
        self.assertTrue('test-steward9' in response.data)

    def test_upload_zip(self):
        ''' Test that a new steward page has a upload form and that it works
        '''
        data = {
            "name" : "Test Steward",
            "email" : "testemail@email.com",
            "url" : "http://testurl.com",
            "phone" : "123456789"
            }

        created = self.app.post('/new-steward', data=data, follow_redirects=True)
        self.assertEqual(created.status_code, 200)
        self.assertTrue('test-steward' in created.data)

        #
        # Check for a file upload field in the home page form.
        #
        soup = BeautifulSoup(created.data)
        form = soup.find('input', attrs=dict(type='file')).find_parent('form')
        self.assertTrue('multipart/form-data' in form['enctype'])
        self.assertTrue(form.find_all('input', attrs=dict(type='file')))

        #
        # Attempt to upload a series of test shapefiles.
        #
        for filename in glob.glob(os.path.join(self.tmp, '*.zip')):
            action = urljoin('/', form['action'])
            input = form.find('input', attrs=dict(type='file'))['name']
            file = open(join(dirname(__file__), filename))
            uploaded = self.app.post(action, data={input: file}, follow_redirects=True)

            self.assertEqual(uploaded.status_code, 200)

if __name__ == '__main__':
    main()
