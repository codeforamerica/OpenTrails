# -- coding: utf-8 --
from shutil import rmtree, copy
from unittest import TestCase, main
from os.path import join, dirname
import os, glob, json
from urlparse import urljoin
from tempfile import mkdtemp
from bs4 import BeautifulSoup

from open_trails import app, transformers
from open_trails.functions import unzip, compress

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
            path = unzip(join(self.tmp, name))
            self.doFileConversion(path)
            
            # clean up - delete uneeded shapefiles
            dont_delete = ['csv','zip','geojson']
            for file in os.listdir(self.tmp):
                if file.split('.')[1] not in dont_delete: 
                    os.remove(self.tmp +'/'+file)

    def doFileConversion(self, path):
        ''' Test conversion results for named file.
        '''
        geojson = transformers.shapefile2geojson(path)

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

        os.mkdir(self.tmp + '/working-dir')

        names = ('test-files/lake-man.zip',
                 'test-files/lake-man-GGNRA.zip',
                 'test-files/lake-man-San-Antonio.zip',
                 'test-files/lake-man-Santa-Clara.zip',
                 'test-files/lake-man-Portland.zip',
                 'test-files/portland-segments.geojson',
                 'test-files/san-antonio-segments.geojson',
                 'test-files/sa-trailheads-test.zip',
                 'test-files/sa-trailheads.geojson')
        for name in names:
            copy(name, os.path.join(self.tmp, 'working-dir'))

        os.mkdir(self.tmp + '/datastore')
        app.config.update(DATASTORE='file://%s/datastore' % self.tmp)

        os.chdir(self.tmp + '/working-dir')

        self.app = app.test_client()

        # Set up file structure of a fake steward
        data = {
            "name" : "Test Steward",
            "url" : "http://testurl.com",
            "phone" : "123456789"
            }
        self.app.post('/new-steward', data=data)

    def tearDown(self):
        rmtree(self.tmp)
        os.chdir(self.dir)

    def test_new_steward(self):
        '''Test creating a new stewards.csv
        '''
        data = {
            "name" : "New Test Steward",
            "url" : "http://newtesturl.com"
            }

        response = self.app.post('/new-steward', data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        # Test that steward info shows up where its supposed to
        soup = BeautifulSoup(response.data)
        name = soup.find(id='steward-name')
        self.assertTrue(data['name'] in name.string)
        url = soup.find(id='steward-url')
        self.assertTrue(data['url'] in url.string)


    def test_stewards_list(self):
        ''' Test that /stewards returns a list of stewards
        '''
        for i in range(1,10):
            data = {
                "name" : "New Test Steward" +str(i),
                "url" : "http://newtesturl"+str(i)+".com",
                "phone" : "123456789"
                }
            self.app.post('/new-steward', data=data)

        response = self.app.get('/stewards')
        self.assertTrue('newtesturl1' in response.data)
        self.assertTrue('newtesturl5' in response.data)
        self.assertTrue('newtesturl9' in response.data)

    def test_existing_steward_only_stewards_csv(self):
        ''' Test accessing a steward at the first step,
            with only a steward.csv file available
        '''
        #
        # Check that page shows test steward
        #
        response = self.app.get("/stewards/testurl")
        self.assertEqual(response.status_code, 200)
        
        # Test that steward info shows up where its supposed to
        soup = BeautifulSoup(response.data)
        name = soup.find(id='steward-name')
        self.assertTrue('Test Steward' in name.string)
        url = soup.find(id='steward-url')
        self.assertTrue('testurl' in url.string)
        
        #
        # Check for a file upload field in the home page form.
        #
        form = soup.find('input', attrs=dict(type='file')).find_parent('form')
        self.assertEqual("/stewards/testurl/upload", form['action'])
        self.assertTrue('multipart/form-data' in form['enctype'])
        self.assertTrue(form.find_all('input', attrs=dict(type='file')))

    def test_upload_zip(self):
        ''' Test uploading zips to the test steward
        '''
        for filepath in glob.glob('*.zip'):
            filename = os.path.split(filepath)[1]
            file = open(filepath)
            self.assertFalse( filename in os.listdir(self.tmp+'/datastore/testurl/uploads'))
            uploaded = self.app.post("/stewards/testurl/upload", data={"file" : file})
            self.assertTrue( filename in os.listdir(self.tmp+'/datastore/testurl/uploads'))
            self.assertEqual(uploaded.status_code, 302)

    def test_show_uploaded_segments(self):
        ''' Show the columns from the uploaded segments
        '''
        file = open('lake-man-Portland.zip')
        response = self.app.post("/stewards/testurl/upload", data={"file": file, "trailtype" : "segments"}, follow_redirects = True)
        file.close()
        file = open('testurl/uploads/lake-man-Portland.geojson')
        original_segments = json.load(file)
        file.close()
        sample_segment = {'type': 'FeatureCollection', 'features': []}
        sample_segment['features'].append(original_segments['features'][0])

        for property in sample_segment['features'][0]['properties']:
            self.assertTrue(property in response.data)

    def test_transform_portland_segments(self):
        ''' Test transforming trail segments
        '''
        # Upload a trail segments zip
        # Test its transformed output
        file = open('lake-man-Portland.zip')
        uploaded = self.app.post("/stewards/testurl/upload", data={"file": file, "trailtype" : "segments"})
        self.assertTrue( 'lake-man-Portland.zip' in os.listdir(self.tmp+'/datastore/testurl/uploads'))
        self.assertEqual(uploaded.status_code, 302)
        self.app.get("/stewards/testurl/transform/segments", follow_redirects=True)

        f = open('testurl/opentrails/segments.geojson')
        opentrails_segments = json.load(f)
        f.close()
        f = open(self.tmp + '/working-dir/portland-segments.geojson')
        expected_geojson = json.load(f)
        f.close()

        self.assertItemsEqual( opentrails_segments, expected_geojson )

    def test_transform_san_antonio_segments(self):
        ''' Test transforming trail segments
        '''
        # Upload a trail segments zip
        # Test its transformed output
        file = open('lake-man-San-Antonio.zip')
        uploaded = self.app.post("/stewards/testurl/upload", data={"file": file, "trailtype" : "segments"})
        self.assertTrue( 'lake-man-San-Antonio.zip' in os.listdir(self.tmp+'/datastore/testurl/uploads'))
        self.assertEqual(uploaded.status_code, 302)
        self.app.get("/stewards/testurl/transform/segments", follow_redirects=True)

        f = open('testurl/opentrails/segments.geojson')
        opentrails_segments = json.load(f)
        f.close()
        f = open(self.tmp + '/working-dir/san-antonio-segments.geojson')
        expected_geojson = json.load(f)
        f.close()

        self.assertItemsEqual( opentrails_segments, expected_geojson )

#     def test_transform_trailheads(self):
#         ''' Test transforming trailheads
#         '''
#         # Upload a trailheads zip
#         # Test its transformed output
#         file = open('sa-trailheads-test.zip')
#         uploaded = self.app.post("/stewards/testurl/upload", data={"file": file, "trailtype" : "trailheads"})
#         self.assertTrue( 'trailheads.zip' in os.listdir(self.tmp+'/datastore/testurl/uploads'))
#         self.assertEqual(uploaded.status_code, 302)
#         transformed = self.app.get("/stewards/testurl/transform/trailheads", follow_redirects=True)
#         f = open(self.tmp + '/working-dir/sa-trailheads.geojson')
#         geojson = f.read()
#         f.close()
#         self.assertTrue( geojson in transformed.data )

#     def test_compress_files(self):
#         compress('portland-segments.geojson','portland-segments.zip')
#         self.assertTrue(os.path.getsize('portland-segments.geojson') > os.path.getsize('portland-segments.zip'))
#         self.assertTrue(os.path.isfile('portland-segments.zip'))


if __name__ == '__main__':
    main()
