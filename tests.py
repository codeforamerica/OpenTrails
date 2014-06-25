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

    def test_segments_conversion_Portland(self):
        ''' Test overall segments conversion.
        '''
        path = unzip(join(self.tmp, 'lake-man-Portland.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        converted_geojson = transformers.segments_transform(geojson, None)
        converted_ids = [f['properties']['id'] for f in converted_geojson['features']]
        expected_ids = [f['properties']['TRAILID'] for f in geojson['features']]
        self.assertEqual(converted_ids, expected_ids)
    
        converted_foots = [f['properties']['foot'] for f in converted_geojson['features']]
        expected_foots = ['yes' for f in geojson['features']]
        self.assertEqual(converted_foots, expected_foots)
    
        converted_bikes = [f['properties']['bicycle'] for f in converted_geojson['features']]
        expected_bikes = ['yes' for f in geojson['features']]
        self.assertEqual(converted_bikes, expected_bikes)
    
        converted_horses = [f['properties']['horse'] for f in converted_geojson['features']]
        expected_horses = [None for f in geojson['features']]
        self.assertEqual(converted_horses, expected_horses)
    
    def test_segments_conversion_San_Antonio(self):
        ''' Test overall segments conversion.
        '''
        path = unzip(join(self.tmp, 'lake-man-San-Antonio.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        converted_geojson = transformers.segments_transform(geojson, None)
        converted_ids = [f['properties']['id'] for f in converted_geojson['features']]
        expected_ids = range(1, len(converted_ids) + 1)
        self.assertEqual(converted_ids, expected_ids)
    
        converted_foots = [f['properties']['foot'] for f in converted_geojson['features']]
        expected_foots = [None for f in geojson['features']]
        self.assertEqual(converted_foots, expected_foots)
    
        converted_bikes = [f['properties']['bicycle'] for f in converted_geojson['features']]
        expected_bikes = [None for f in geojson['features']]
        self.assertEqual(converted_bikes, expected_bikes)
    
        converted_horses = [f['properties']['horse'] for f in converted_geojson['features']]
        expected_horses = [None for f in geojson['features']]
        self.assertEqual(converted_horses, expected_horses)
    
    def test_segments_conversion_GGNRA(self):
        ''' Test overall segments conversion.
        '''
        path = unzip(join(self.tmp, 'lake-man-GGNRA.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        converted_geojson = transformers.segments_transform(geojson, None)
        converted_ids = [f['properties']['id'] for f in converted_geojson['features']]
        expected_ids = range(1, len(converted_ids) + 1)
        self.assertEqual(converted_ids, expected_ids)
        
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
    
    def test_segments_conversion_Santa_Clara(self):
        ''' Test overall segments conversion.
        '''
        path = unzip(join(self.tmp, 'lake-man-Santa-Clara.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        converted_geojson = transformers.segments_transform(geojson, None)
        converted_ids = [f['properties']['id'] for f in converted_geojson['features']]
        expected_ids = [f['properties']['OBJECTID'] for f in geojson['features']]
        self.assertEqual(converted_ids, expected_ids)
        
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
    
    def test_finding_segment_IDs_Portland(self):
        ''' Test search for trail segment IDs.
        
            See also https://github.com/codeforamerica/PLATS/issues/26
        '''
        path = unzip(join(self.tmp, 'lake-man-Portland.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        original_properties = [f['properties'] for f in geojson['features']]
        found_ids = map(transformers.find_segment_id, original_properties)
        self.assertEqual(found_ids, [p['TRAILID'] for p in original_properties])

    def test_finding_segment_IDs_San_Antonio(self):
        ''' Test search for trail segment IDs.
        
            See also https://github.com/codeforamerica/PLATS/issues/26
        '''
        path = unzip(join(self.tmp, 'lake-man-San-Antonio.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        original_properties = [f['properties'] for f in geojson['features']]
        found_ids = map(transformers.find_segment_id, original_properties)
        self.assertEqual(found_ids, [None for id in found_ids])

    def test_finding_segment_IDs_GGNRA(self):
        ''' Test search for trail segment IDs.
        
            See also https://github.com/codeforamerica/PLATS/issues/26
        '''
        path = unzip(join(self.tmp, 'lake-man-GGNRA.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        original_properties = [f['properties'] for f in geojson['features']]
        found_ids = map(transformers.find_segment_id, original_properties)
        self.assertEqual(found_ids, [None for id in found_ids])

    def test_finding_segment_IDs_Santa_Clara(self):
        ''' Test search for trail segment IDs.
        
            See also https://github.com/codeforamerica/PLATS/issues/26
        '''
        path = unzip(join(self.tmp, 'lake-man-Santa-Clara.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        original_properties = [f['properties'] for f in geojson['features']]
        found_ids = map(transformers.find_segment_id, original_properties)
        self.assertEqual(found_ids, [p['OBJECTID'] for p in original_properties])
    
    def test_finding_segment_foot_use_Portland(self):
        ''' Test search for trail foot use.
        
            See also https://github.com/codeforamerica/PLATS/issues/28
        '''
        path = unzip(join(self.tmp, 'lake-man-Portland.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        original_properties = [f['properties'] for f in geojson['features']]
        found_ids = map(transformers.find_segment_foot_use, original_properties)
        self.assertEqual(found_ids, ['yes' for id in found_ids])

    def test_finding_segment_foot_use_San_Antonio(self):
        ''' Test search for trail foot use.
        
            See also https://github.com/codeforamerica/PLATS/issues/28
        '''
        path = unzip(join(self.tmp, 'lake-man-San-Antonio.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        original_properties = [f['properties'] for f in geojson['features']]
        found_ids = map(transformers.find_segment_foot_use, original_properties)
        self.assertEqual(found_ids, [None for id in found_ids])

    def test_finding_segment_foot_use_GGNRA(self):
        ''' Test search for trail foot use.
        
            See also https://github.com/codeforamerica/PLATS/issues/28
        '''
        path = unzip(join(self.tmp, 'lake-man-GGNRA.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        original_properties = [f['properties'] for f in geojson['features']]
        found_ids = map(transformers.find_segment_foot_use, original_properties)
        
        uses = {'Multi-Use': 'yes', 'Hiking': 'yes', 'Hiking and Horses': 'yes'}
        self.assertEqual(found_ids, [uses.get(p['use_type'], None) for p in original_properties])

    def test_finding_segment_foot_use_Santa_Clara(self):
        ''' Test search for trail foot use.
        
            See also https://github.com/codeforamerica/PLATS/issues/28
        '''
        path = unzip(join(self.tmp, 'lake-man-Santa-Clara.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        original_properties = [f['properties'] for f in geojson['features']]
        found_ids = map(transformers.find_segment_foot_use, original_properties)
        
        uses = {'hiking': 'yes', 'hiking/equestrian': 'yes', 'hiking/equestrian/bicycling': 'yes'}
        self.assertEqual(found_ids, [uses.get(p['PUBUSE'], None) for p in original_properties])

    def test_finding_segment_bicycle_use_Portland(self):
        ''' Test search for trail bicycle use.
        
            See also https://github.com/codeforamerica/PLATS/issues/29
        '''
        path = unzip(join(self.tmp, 'lake-man-Portland.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        original_properties = [f['properties'] for f in geojson['features']]
        found_ids = map(transformers.find_segment_bicycle_use, original_properties)
        self.assertEqual(found_ids, [p['ROADBIKE'].lower() for p in original_properties])

    def test_finding_segment_bicycle_use_San_Antonio(self):
        ''' Test search for trail bicycle use.
        
            See also https://github.com/codeforamerica/PLATS/issues/29
        '''
        path = unzip(join(self.tmp, 'lake-man-San-Antonio.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        original_properties = [f['properties'] for f in geojson['features']]
        found_ids = map(transformers.find_segment_bicycle_use, original_properties)
        self.assertEqual(found_ids, [None for id in found_ids])

    def test_finding_segment_bicycle_use_GGNRA(self):
        ''' Test search for trail bicycle use.
        
            See also https://github.com/codeforamerica/PLATS/issues/29
        '''
        path = unzip(join(self.tmp, 'lake-man-GGNRA.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        original_properties = [f['properties'] for f in geojson['features']]
        found_ids = map(transformers.find_segment_bicycle_use, original_properties)
        
        uses = {'Multi-Use': 'yes', 'Hiking': 'no'}
        self.assertEqual(found_ids, [uses.get(p['use_type'], None) for p in original_properties])

    def test_finding_segment_bicycle_use_Santa_Clara(self):
        ''' Test search for trail bicycle use.
        
            See also https://github.com/codeforamerica/PLATS/issues/29
        '''
        path = unzip(join(self.tmp, 'lake-man-Santa-Clara.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        original_properties = [f['properties'] for f in geojson['features']]
        found_ids = map(transformers.find_segment_bicycle_use, original_properties)
        
        uses = {'hiking': 'no', 'hiking/equestrian': 'no', 'hiking/equestrian/bicycling': 'yes'}
        self.assertEqual(found_ids, [uses.get(p['PUBUSE'], None) for p in original_properties])

    def test_finding_segment_horse_use_Portland(self):
        ''' Test search for trail horse use.
        
            See also https://github.com/codeforamerica/PLATS/issues/30
        '''
        path = unzip(join(self.tmp, 'lake-man-Portland.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        original_properties = [f['properties'] for f in geojson['features']]
        found_ids = map(transformers.find_segment_horse_use, original_properties)
        self.assertEqual(found_ids, [None for p in original_properties])

    def test_finding_segment_horse_use_San_Antonio(self):
        ''' Test search for trail horse use.
        
            See also https://github.com/codeforamerica/PLATS/issues/30
        '''
        path = unzip(join(self.tmp, 'lake-man-San-Antonio.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        original_properties = [f['properties'] for f in geojson['features']]
        found_ids = map(transformers.find_segment_horse_use, original_properties)
        self.assertEqual(found_ids, [None for id in found_ids])

    def test_finding_segment_horse_use_GGNRA(self):
        ''' Test search for trail horse use.
        
            See also https://github.com/codeforamerica/PLATS/issues/30
        '''
        path = unzip(join(self.tmp, 'lake-man-GGNRA.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        original_properties = [f['properties'] for f in geojson['features']]
        found_ids = map(transformers.find_segment_horse_use, original_properties)
        
        uses = {'Multi-Use': 'no', 'Hiking': 'no'}
        self.assertEqual(found_ids, [uses.get(p['use_type'], None) for p in original_properties])

    def test_finding_segment_horse_use_Santa_Clara(self):
        ''' Test search for trail horse use.
        
            See also https://github.com/codeforamerica/PLATS/issues/30
        '''
        path = unzip(join(self.tmp, 'lake-man-Santa-Clara.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        original_properties = [f['properties'] for f in geojson['features']]
        found_ids = map(transformers.find_segment_horse_use, original_properties)
        
        uses = {'hiking': 'no', 'hiking/equestrian': 'yes', 'hiking/equestrian/bicycling': 'yes'}
        self.assertEqual(found_ids, [uses.get(p['PUBUSE'], None) for p in original_properties])

    def test_finding_segment_ski_use_Portland(self):
        ''' Test search for trail ski use.
        
            See also https://github.com/codeforamerica/PLATS/issues/31
        '''
        path = unzip(join(self.tmp, 'lake-man-Portland.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        original_properties = [f['properties'] for f in geojson['features']]
        found_ids = map(transformers.find_segment_ski_use, original_properties)
        self.assertEqual(found_ids, [None for p in original_properties])

    def test_finding_segment_ski_use_GGNRA(self):
        ''' Test search for trail ski use.
        
            See also https://github.com/codeforamerica/PLATS/issues/31
        '''
        path = unzip(join(self.tmp, 'lake-man-GGNRA.zip'))
        geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
        original_properties = [f['properties'] for f in geojson['features']]
        found_ids = map(transformers.find_segment_ski_use, original_properties)
        self.assertEqual(found_ids, ['yes', 'no', 'yes', 'yes', None, 'yes'])

    # def test_finding_segment_ski_use_Santa_Clara(self):
    #     ''' Test search for trail ski use.
        
    #         See also https://github.com/codeforamerica/PLATS/issues/31
    #     '''
    #     path = unzip(join(self.tmp, 'lake-man-Santa-Clara.zip'))
    #     geojson = transformers.shapefile2geojson(join(self.tmp, path))
        
    #     original_properties = [f['properties'] for f in geojson['features']]
    #     found_ids = map(transformers.find_segment_ski_use, original_properties)
    #     self.assertEqual(found_ids, ['yes', 'no', 'yes', 'yes', None, 'yes'])

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

    def test_new_dataset(self):
        '''Test creating a new .valid
        '''

        response = self.app.post('/new-dataset', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        datastore = make_datastore(self.config['DATASTORE'])

        # Ensure there is exactly one file and that it's called ".valid"
        (filename, ) = datastore.filelist('')
        self.assertTrue(filename.endswith('/.valid'))

        # # Test that steward info shows up where its supposed to
        # soup = BeautifulSoup(response.data)
        # name = soup.find(id='steward-name')
        # self.assertTrue(data['name'] in name.string)
        # url = soup.find(id='steward-url')
        # self.assertTrue(data['url'] in url.string)


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
