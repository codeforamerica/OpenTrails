# -- coding: utf-8 --
from shutil import rmtree, copy
from unittest import TestCase, main
from os.path import join, dirname
import os
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
        
        os.chdir(self.tmp)

    def tearDown(self):
        rmtree(self.tmp)
        os.chdir(self.dir)

    def testConvert(self):
        ''' Test basic SHP to GeoJSON conversion.
        '''
        for name in os.listdir(self.tmp):
            path = unzip(join(self.tmp,name))
            self.doFileConversion(path)

    def doFileConversion(self, path):
        ''' Test conversion results for named file.
        '''
        file = join(dirname(__file__), path)
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


def whooo():
    print "WHOOOOO"

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

    #@patch('open_trails.routes.new_steward')
    def test_new_stewards(self):
        '''Test creating a new stewards.csv
        '''
        data = {
            "name" : "Test Steward",
            "email" : "testemail@email.com",
            "url" : "http://testurl.com",
            "phone" : "123456789"
            }
        #import pdb; pdb.set_trace()
        response = self.app.post('/new-steward', data=data, follow_redirects=True)
        #mock_new_steward.make_folders.assert_called()
        self.assertEqual(response.status_code, 200)
        self.assertTrue('test-steward' in response.data)
    #
    #
    #
    # def testUpload(self):
    #     ''' Check basic file upload flow.
    #     '''
    #
    #     for name in os.listdir(self.tmp):
    #         self.doUpload(name)
    #
    # def doUpload(self, name):
    #     ''' Check basic file upload flow for named file.
    #     '''
    #     response = self.app.get('/')
    #     self.assertEqual(response.status_code, 200)
    #
    #     #
    #     # Check for a file upload field in the home page form.
    #     #
    #     soup = BeautifulSoup(response.data)
    #     form = soup.find('input', attrs=dict(type='file')).find_parent('form')
    #     self.assertTrue('multipart/form-data' in form['enctype'])
    #     self.assertTrue(form.find_all('input', attrs=dict(type='file')))
    #
    #     #
    #     # Attempt to upload a test shapefile.
    #     #
    #     action = urljoin('/', form['action'])
    #     input = form.find('input', attrs=dict(type='file'))['name']
    #     file = open(join(dirname(__file__), name))
    #     response = self.app.post(action, data={input: file})
    #
    #     self.assertEqual(response.status_code, 200)
    #
    # def testOpenThreeZippedShapefiles(self):
    #     ''' Tests openning of a zipfile containing three zipped shapefiles
    #     '''
    #     self.doUpload("test-files/sa-test-files.zip")

if __name__ == '__main__':
    main()
