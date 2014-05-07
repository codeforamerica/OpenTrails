import os
from flask import Flask, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
import zipfile
import json

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = set(['zip'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def unzipfile(filepath):
    zf = zipfile.ZipFile(filepath, 'r')
    zf.extractall(app.config['UPLOAD_FOLDER'])
    for name in zf.namelist():
        if name.rsplit('.', 1)[1] == 'shp':
            return name

def shp2geojson(filename):
    import subprocess
    # HEROKU
    subprocess.call("/app/vendor/gdal/bin/ogr2ogr -t_srs EPSG:4326 -f GeoJSON uploads/"+filename+".geojson " + os.path.join(app.config['UPLOAD_FOLDER'], filename), shell=True)
    # LOCAL DEV
    # subprocess.call("/Library/Frameworks/GDAL.framework/Versions/Current/Programs/ogr2ogr -t_srs EPSG:4326 -f GeoJSON uploads/"+filename+".geojson " + os.path.join(app.config['UPLOAD_FOLDER'], filename), shell=True)
    return "uploads/"+filename+".geojson"

def open_geojson(geojson_path):

    json_data=open(geojson_path)
    data = json.load(json_data)
    json_data.close()
    return data

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            shapefile_path = unzipfile('uploads/'+filename)
            # srid = request.form['srid']
            geojson_path = shp2geojson(shapefile_path)
            data = open_geojson(geojson_path)
            return json.dumps(data)

    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)

if __name__ == "__main__":
    app.run(debug=True)
