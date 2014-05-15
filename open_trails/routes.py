from open_trails import app
from open_trails.upload import upload_s3, download_s3
from open_trails.transformers import unzipfile
from flask import request, render_template
import json

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    data_url = upload_s3(request.form['org-name'], request.files['file'])

# @app.route('/map', methods=['POST'])
# def map():
#     data = transformers.transform_shapefile(shapefile)
#     return render_template('map.html', data = data)

@app.route('/map/<org_name>')
def map_existing_org(org_name):
    import pdb; pdb.set_trace()
    filepath = download_s3(org_name)
    return unzipfile(filepath)
