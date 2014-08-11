# -- coding: utf-8 --
from shutil import rmtree, copy
from unittest import TestCase, main
from os.path import join, dirname
import os, glob, json, re
from urlparse import urljoin
from tempfile import mkdtemp
from bs4 import BeautifulSoup
from zipfile import ZipFile
from StringIO import StringIO

from open_trails import app, transformers, validators
from open_trails.functions import unzip, compress
from open_trails.models import make_datastore

class FakeUpload:
    ''' Pretend to be a file upload in flask.
    '''
    def __init__(self, path):
        self._file = open(path, 'r')
        self.filename = path

    def save(self, path):
        with open(path, 'w') as file:
            file.write(self._file.read())

class TestValidators (TestCase):

    def setUp(self):
        self.dir = os.getcwd()
        self.tmp = mkdtemp(prefix='plats-')

        names = ('test-files/open-trails-GGNRA.zip',)
        for name in names:
            copy(name, self.tmp)

    def tearDown(self):
        rmtree(self.tmp)
    
    def test_validate_GGNRA(self):
        '''
        '''
        unzip(join(self.tmp, 'open-trails-GGNRA.zip'), None, ('.geojson', '.csv'))
        
        files = (join(self.tmp, 'trail_segments.geojson'),
                 join(self.tmp, 'named_trails.csv'),
                 join(self.tmp, 'trailheads.geojson'),
                 join(self.tmp, 'stewards.csv'),
                 join(self.tmp, 'areas.geojson')
                 )
        
        messages, result = validators.check_open_trails(*files)
        
        self.assertFalse(result)
        
        expected_messages = [
            ('error', 'bad-data-stewards', 'Required stewards field "license" is missing.'),
            ('success', 'valid-file-trail-segments', 'Your trail-segments.geojson file looks good.'),
            ('success', 'valid-file-named-trails', 'Your named-trails.csv file looks good.'),
            ('warning', 'bad-data-trailheads', 'Optional trailheads field "area_id" is missing.'),
            ('warning', 'missing-file-areas', 'Could not find optional file areas.geojson.'),
            ]
        
        self.assertEqual(len(messages), len(expected_messages))
        
        for expected in expected_messages:
            self.assertTrue(expected in messages, expected)

class TestTransformers (TestCase):

    def setUp(self):
        self.dir = os.getcwd()
        self.tmp = mkdtemp(prefix='plats-')

        names = ('test-files/lake-man.zip',
                 'test-files/lake-man-GGNRA.zip',
                 'test-files/lake-man-San-Antonio.zip',
                 'test-files/lake-man-Santa-Clara.zip',
                 'test-files/lake-man-Portland.zip',
                 'test-files/lake-man-Nested.zip',
                 'test-files/lake-man-EBRPD.zip')
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

    def test_segments_conversion_Portland(self):
        ''' Test overall segments conversion.
        '''
        path = unzip(join(self.tmp, 'lake-man-Portland.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        m, converted_geojson = transformers.segments_transform(geojson, None)
        self.assertEqual(len(m), 2)

        converted_ids = [f['properties']['id'] for f in converted_geojson['features']]
        expected_ids = [f['properties']['TRAILID'] for f in geojson['features']]
        self.assertEqual(converted_ids, expected_ids)
    
        converted_names = [f['properties']['name'] for f in converted_geojson['features']]
        expected_names = [f['properties']['TRAILNAME'] for f in geojson['features']]
        self.assertEqual(converted_names, expected_names)
    
        converted_foots = [f['properties']['foot'] for f in converted_geojson['features']]
        expected_foots = ['yes' for f in geojson['features']]
        self.assertEqual(converted_foots, expected_foots)
    
        converted_bikes = [f['properties']['bicycle'] for f in converted_geojson['features']]
        expected_bikes = ['yes' for f in geojson['features']]
        self.assertEqual(converted_bikes, expected_bikes)
    
        converted_horses = [f['properties']['horse'] for f in converted_geojson['features']]
        expected_horses = [None for f in geojson['features']]
        self.assertEqual(converted_horses, expected_horses)
    
        converted_skis = [f['properties']['ski'] for f in converted_geojson['features']]
        expected_skis = [None for f in geojson['features']]
        self.assertEqual(converted_skis, expected_skis)
    
        converted_wheelchairs = [f['properties']['wheelchair'] for f in converted_geojson['features']]
        expected_wheelchairs = [None for f in geojson['features']]
        self.assertEqual(converted_wheelchairs, expected_wheelchairs)
    
        converted_motor_vehicles = [f['properties']['motor_vehicles'] for f in converted_geojson['features']]
        expected_motor_vehicles = [None for f in geojson['features']]
        self.assertEqual(converted_motor_vehicles, expected_motor_vehicles)
    
    def test_segments_conversion_San_Antonio(self):
        ''' Test overall segments conversion.
        '''
        path = unzip(join(self.tmp, 'lake-man-San-Antonio.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        m, converted_geojson = transformers.segments_transform(geojson, None)
        self.assertEqual(len(m), 7)

        converted_ids = [f['properties']['id'] for f in converted_geojson['features']]
        expected_ids = map(str, range(1, len(converted_ids) + 1))
        self.assertEqual(converted_ids, expected_ids)
    
        converted_names = [f['properties']['name'] for f in converted_geojson['features']]
        expected_names = [f['properties']['Name'] for f in geojson['features']]
        self.assertEqual(converted_names, expected_names)
    
        converted_foots = [f['properties']['foot'] for f in converted_geojson['features']]
        expected_foots = [None for f in geojson['features']]
        self.assertEqual(converted_foots, expected_foots)
    
        converted_bikes = [f['properties']['bicycle'] for f in converted_geojson['features']]
        expected_bikes = [None for f in geojson['features']]
        self.assertEqual(converted_bikes, expected_bikes)
    
        converted_horses = [f['properties']['horse'] for f in converted_geojson['features']]
        expected_horses = [None for f in geojson['features']]
        self.assertEqual(converted_horses, expected_horses)
    
        converted_skis = [f['properties']['ski'] for f in converted_geojson['features']]
        expected_skis = [None for f in geojson['features']]
        self.assertEqual(converted_skis, expected_skis)
    
        converted_wheelchairs = [f['properties']['wheelchair'] for f in converted_geojson['features']]
        expected_wheelchairs = [None for f in geojson['features']]
        self.assertEqual(converted_wheelchairs, expected_wheelchairs)
    
        converted_motor_vehicles = [f['properties']['motor_vehicles'] for f in converted_geojson['features']]
        expected_motor_vehicles = [None for f in geojson['features']]
        self.assertEqual(converted_motor_vehicles, expected_motor_vehicles)
    
    def test_segments_conversion_GGNRA(self):
        ''' Test overall segments conversion.
        '''
        path = unzip(join(self.tmp, 'lake-man-GGNRA.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        m, converted_geojson = transformers.segments_transform(geojson, None)
        self.assertEqual(len(m), 2)

        converted_ids = [f['properties']['id'] for f in converted_geojson['features']]
        expected_ids = map(str, range(1, len(converted_ids) + 1))
        self.assertEqual(converted_ids, expected_ids)
    
        converted_names = [f['properties']['name'] for f in converted_geojson['features']]
        expected_names = [f['properties']['trail_name'] for f in geojson['features']]
        self.assertEqual(converted_names, expected_names)
        
        uses = {'Multi-Use': 'yes', 'Hiking': 'yes', 'Hiking and Horses': 'yes'}
        converted_foots = [f['properties']['foot'] for f in converted_geojson['features']]
        expected_foots = [uses.get(f['properties']['use_type'], None) for f in geojson['features']]
        self.assertEqual(converted_foots, expected_foots)
        
        uses = {'Multi-Use': 'yes', 'Hiking': 'no', 'Hiking and Horses': 'no'}
        converted_bikes = [f['properties']['bicycle'] for f in converted_geojson['features']]
        expected_bikes = [uses.get(f['properties']['use_type'], None) for f in geojson['features']]
        self.assertEqual(converted_bikes, expected_bikes)
        
        uses = {'Multi-Use': 'no', 'Hiking': 'no', 'Hiking and Horses': 'yes'}
        converted_horses = [f['properties']['horse'] for f in converted_geojson['features']]
        expected_horses = [uses.get(f['properties']['use_type'], None) for f in geojson['features']]
        self.assertEqual(converted_horses, expected_horses)
    
        converted_skis = [f['properties']['ski'] for f in converted_geojson['features']]
        expected_skis = ['yes', 'no', 'yes', 'yes', None, 'yes']
        self.assertEqual(converted_skis, expected_skis)
    
        converted_wheelchairs = [f['properties']['wheelchair'] for f in converted_geojson['features']]
        expected_wheelchairs = [None] * 6
        self.assertEqual(converted_wheelchairs, expected_wheelchairs)
    
        converted_motor_vehicles = [f['properties']['motor_vehicles'] for f in converted_geojson['features']]
        expected_motor_vehicles = [None for f in geojson['features']]
        self.assertEqual(converted_motor_vehicles, expected_motor_vehicles)
    
    def test_segments_conversion_Santa_Clara(self):
        ''' Test overall segments conversion.
        '''
        path = unzip(join(self.tmp, 'lake-man-Santa-Clara.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        m, converted_geojson = transformers.segments_transform(geojson, None)
        self.assertEqual(len(m), 2)

        converted_ids = [f['properties']['id'] for f in converted_geojson['features']]
        expected_ids = [f['properties']['OBJECTID'] for f in geojson['features']]
        self.assertEqual(converted_ids, expected_ids)
    
        converted_names = [f['properties']['name'] for f in converted_geojson['features']]
        expected_names = [f['properties']['NAME'] for f in geojson['features']]
        self.assertEqual(converted_names, expected_names)
        
        uses = {'hiking': 'yes', 'hiking/equestrian': 'yes', 'hiking/equestrian/bicycling': 'yes'}
        converted_foots = [f['properties']['foot'] for f in converted_geojson['features']]
        expected_foots = [uses.get(f['properties']['PUBUSE'], None) for f in geojson['features']]
        self.assertEqual(converted_foots, expected_foots)
        
        uses = {'hiking': 'no', 'hiking/equestrian': 'no', 'hiking/equestrian/bicycling': 'yes'}
        converted_bikes = [f['properties']['bicycle'] for f in converted_geojson['features']]
        expected_bikes = [uses.get(f['properties']['PUBUSE'], None) for f in geojson['features']]
        self.assertEqual(converted_bikes, expected_bikes)
        
        uses = {'hiking': 'no', 'hiking/equestrian': 'yes', 'hiking/equestrian/bicycling': 'yes'}
        converted_horses = [f['properties']['horse'] for f in converted_geojson['features']]
        expected_horses = [uses.get(f['properties']['PUBUSE'], None) for f in geojson['features']]
        self.assertEqual(converted_horses, expected_horses)
    
        converted_skis = [f['properties']['ski'] for f in converted_geojson['features']]
        expected_skis = ['no' for f in geojson['features']]
        self.assertEqual(converted_skis, expected_skis)
    
        converted_wheelchairs = [f['properties']['wheelchair'] for f in converted_geojson['features']]
        expected_wheelchairs = [None for f in geojson['features']]
        self.assertEqual(converted_wheelchairs, expected_wheelchairs)
    
        converted_motor_vehicles = [f['properties']['motor_vehicles'] for f in converted_geojson['features']]
        expected_motor_vehicles = [None for f in geojson['features']]
        self.assertEqual(converted_motor_vehicles, expected_motor_vehicles)

    def test_segments_conversion_Nested(self):
        ''' Test overall segments conversion.
        '''
        path = unzip(join(self.tmp, 'lake-man-Nested.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        m, converted_geojson = transformers.segments_transform(geojson, None)
        self.assertEqual(len(m), 2)
    
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
                 'test-files/open-trails-GGNRA.zip',
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
        self.config = app.config

        # Set up file structure of a fake steward
        # data = {
        #     "name" : "Test Steward",
        #     "url" : "http://testurl.com",
        #     "phone" : "123456789"
        #     }
        # self.app.post('/new-steward', data=data)

    def tearDown(self):
        rmtree(self.tmp)
        os.chdir(self.dir)

    def test_convert_Portland(self):
        ''' Test starting a new data set, and uploading segments.
        '''
        started = self.app.post('/new-dataset', follow_redirects=True)
        self.assertEqual(started.status_code, 200)
        
        datastore = make_datastore(self.config['DATASTORE'])

        # Ensure there is exactly one file and that it's called ".valid"
        (filename, ) = datastore.filelist('')
        self.assertTrue(filename.endswith('/.valid'))

        #
        # Check for a file upload field in the home page form.
        #
        soup = BeautifulSoup(started.data)
        form = soup.find('input', attrs=dict(type='file')).find_parent('form')
        self.assertTrue(form['action'].startswith('/datasets'))
        self.assertTrue(form['action'].endswith('/upload'))
        self.assertTrue('multipart/form-data' in form['enctype'])
        self.assertTrue(form.find_all('input', attrs=dict(type='file')))

        # Upload a zipped shapefile
        file = open(os.path.join(self.tmp, 'working-dir', 'lake-man-Portland.zip'))
        uploaded1 = self.app.post(form['action'], data={"file" : file}, follow_redirects=True)
        self.assertTrue('714115' in uploaded1.data)

        soup = BeautifulSoup(uploaded1.data)
        form = soup.find('button').find_parent('form')
        self.assertTrue(form['action'].startswith('/datasets'))
        self.assertTrue(form['action'].endswith('/transform-segments'))

        # Do the transforming
        transformed1 = self.app.post(form['action'], follow_redirects=True)
        self.assertTrue('714115' in transformed1.data)
        
        soup = BeautifulSoup(transformed1.data)
        form = soup.find('button').find_parent('form')
        self.assertTrue(form['action'].startswith('/datasets'))
        self.assertTrue(form['action'].endswith('/name-trails'))
        
        # Ask to name the trails
        named = self.app.post(form['action'], follow_redirects=True)

        soup = BeautifulSoup(named.data)
        form = soup.find('input', attrs=dict(name='name')).find_parent('form')
        self.assertTrue(form['action'].startswith('/datasets'))
        self.assertTrue(form['action'].endswith('/create-steward'))
        
        # Submit stewards information
        args = dict(name='Winterfell', url='http://codeforamerica.org/governments/winterfell/')
        stewarded = self.app.post(form['action'], data=args, follow_redirects=True)
        
        #
        # Check for a file upload field in the next page form.
        #
        soup = BeautifulSoup(stewarded.data)
        form = soup.find('input', attrs=dict(type='file')).find_parent('form')
        self.assertTrue(form['action'].startswith('/datasets'))
        self.assertTrue(form['action'].endswith('/upload-trailheads'))
        self.assertTrue('multipart/form-data' in form['enctype'])
        self.assertTrue(form.find_all('input', attrs=dict(type='file')))

        # Upload a zipped shapefile
        file = open(os.path.join(self.tmp, 'working-dir', 'sa-trailheads-test.zip'))
        uploaded2 = self.app.post(form['action'], data={"file" : file}, follow_redirects=True)
        self.assertTrue('Comanche' in uploaded2.data)

        soup = BeautifulSoup(uploaded2.data)
        form = soup.find('button').find_parent('form')
        self.assertTrue(form['action'].startswith('/datasets'))
        self.assertTrue(form['action'].endswith('/transform-trailheads'))

        # Do the transforming
        transformed2 = self.app.post(form['action'], follow_redirects=True)
        self.assertTrue('Comanche' in transformed2.data)
        
        soup = BeautifulSoup(transformed2.data)
        link = soup.find('a', attrs=dict(href=re.compile(r'.+\.zip$')))
        
        zipfile = self.app.get(link['href'])
        zipfile = ZipFile(StringIO(zipfile.data))
        
        self.assertTrue('trail_segments.geojson' in zipfile.namelist())
        self.assertTrue('trailheads.geojson' in zipfile.namelist())
        self.assertTrue('named_trails.csv' in zipfile.namelist())
        self.assertTrue('stewards.csv' in zipfile.namelist())

    def test_validate_GGNRA(self):
        ''' Test starting a new data set, and uploading segments.
        '''
        response = self.app.post('/check-dataset', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        datastore = make_datastore(self.config['DATASTORE'])

        # Ensure there is exactly one file and that it's called ".valid"
        (filename, ) = datastore.filelist('')
        self.assertTrue(filename.endswith('/.valid'))

        #
        # Check for a file upload field in the home page form.
        #
        soup = BeautifulSoup(response.data)
        form = soup.find('input', attrs=dict(type='file')).find_parent('form')
        self.assertTrue(form['action'].startswith('/checks'))
        self.assertTrue(form['action'].endswith('/upload'))
        self.assertTrue('multipart/form-data' in form['enctype'])
        self.assertTrue(form.find_all('input', attrs=dict(type='file')))

        # Upload a zipped shapefile
        file = open(os.path.join(self.tmp, 'working-dir', 'open-trails-GGNRA.zip'))
        uploaded = self.app.post(form['action'], data={"file" : file}, follow_redirects=True)
        self.assertTrue('Notes' in uploaded.data)
        
        # Check for some error notes
        soup = BeautifulSoup(uploaded.data)
        self.assertTrue(soup.find(text='Optional trailheads field "area_id" is missing.'))
        self.assertTrue(soup.find(text='Required stewards field "license" is missing.'))
        self.assertTrue(soup.find(text='Could not find optional file areas.geojson.'))

    def do_not_test_stewards_list(self):
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

    def do_not_test_existing_steward_only_stewards_csv(self):
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

    def do_not_test_upload_zip(self):
        ''' Test uploading zips to the test steward
        '''
        for filepath in glob.glob('*.zip'):
            filename = os.path.split(filepath)[1]
            file = open(filepath)
            self.assertFalse( filename in os.listdir(self.tmp+'/datastore/testurl/uploads'))
            uploaded = self.app.post("/stewards/testurl/upload", data={"file" : file})
            self.assertTrue( filename in os.listdir(self.tmp+'/datastore/testurl/uploads'))
            self.assertEqual(uploaded.status_code, 302)

    def do_not_test_show_uploaded_segments(self):
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

    def do_not_test_transform_portland_segments(self):
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

    def do_not_test_transform_san_antonio_segments(self):
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
