# -- coding: utf-8 --
from shutil import rmtree
from unittest import TestCase, main
from os.path import join, dirname
from urlparse import urljoin
from tempfile import mkdtemp

from bs4 import BeautifulSoup

from open_trails import app, transformers

class TestApp (TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.tmp = mkdtemp(prefix='plats-')
        app.config['UPLOAD_FOLDER'] = self.tmp
    
    def tearDown(self):
        rmtree(self.tmp)
    
    def test_upload(self):
        ''' Check basic file upload flow.
        '''
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        
        #
        # Check for a file upload field in the home page form.
        #
        soup = BeautifulSoup(response.data)
        form = soup.find('input', attrs=dict(type='file')).find_parent('form')
        self.assertTrue('multipart/form-data' in form['enctype'])
        self.assertTrue(form.find_all('input', attrs=dict(type='file')))
        
        #
        # Attempt to upload a test shapefile.
        #
        action = urljoin('/', form['action'])
        input = form.find('input', attrs=dict(type='file'))['name']
        file = open(join(dirname(__file__), 'test-files/lake-man.zip'))
        response = self.app.post(action, data={input: file})
        
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    main()
