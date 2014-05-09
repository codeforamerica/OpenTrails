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
    # Unzips an archive and searches for the contained .shp file
    # Returns the path to that .shp file
    zf = zipfile.ZipFile(filepath, 'r')
    zf.extractall(app.config['UPLOAD_FOLDER'])
    for name in zf.namelist():
        if name.rsplit('.', 1)[1] == 'shp':
            return name

def shp2geojson(filename):
    # Converts a shapefile to a geojson file with spherical mercator.
    import subprocess
    subprocess.call("ogr2ogr -t_srs EPSG:4326 -f GeoJSON uploads/"+filename+".geojson " + os.path.join(app.config['UPLOAD_FOLDER'], filename), shell=True)
    return "uploads/"+filename+".geojson"

def open_geojson(geojson_path):
    # Reads a geojson file.
    json_data=open(geojson_path)
    data = json.load(json_data)
    json_data.close()
    return data

def give_ids_to_namedtrails(data):
    # Gives each trail name a unique id
    trail_name_ids = {}
    unique_trail_id = 1
    import pdb; pdb.set_trace()
    for trail in data['features']:
        for trailid in range(1,6):
            if trail['properties']["trail"+str(trailid)]:
                if trail['properties']["trail"+str(trailid)] not in trail_name_ids:
                    trail_name_ids[trail['properties']["trail"+str(trailid)]] = unique_trail_id
                    unique_trail_id += 1
    return trail_name_ids

def create_namedtrails(data):
    # Creates a namedtrails csv
    namedtrails = []
    import pdb; pdb.set_trace()
    trail_name_ids = give_ids_to_namedtrails(data)
    unique_id = 1
    for trail in data['features']:
        namedtrail = []
        segment_ids = []
        namedtrail.append("NAME")
        for trailid in range(1,6):
            if trail['properties']["trail"+str(trailid)]:
                segment_ids.append(trail_name_ids[trail['properties']["trail"+str(trailid)]])
        namedtrail.append(segment_ids)
        namedtrail.append(unique_id)
        unique_id += 1
        description = "DESCRIPTION"
        namedtrail.append(description)
        designation = "DESIGNATION"
        namedtrail.append(designation)
        part_of = "PART OF"
        namedtrail.append(part_of)

        namedtrails.append(namedtrail)

    return namedtrails

def write_namedtrails(namedtrails):
    import csv

    with open("namedtrails.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerows(namedtrails)


def yes_or_no(attribute):
    # Simple yes or no attributes
    if attribute == "Y":
        return "yes"
    elif attribute == "N":
        return "no"
    # else:
    #     import pdb; pdb.set_trace()
    #     raise ValueError

def get_address(properties):
    # Address
    return properties['Address']

def get_trail_ids(properties):
    # TrailIds
    trail_ids = []
    for trailid in range(1,6):
        if properties["Trail"+str(trailid)]:
            trail_ids.append(properties["Trail"+str(trailid)])
    return trail_ids

def convert2open_trails(data):
    # New blank collection of trailheads
    ot_data = {
        "type" : "FeatureCollection",
        "features" : []
    }
    for trailhead in data['features']:
        # New blank ot_trailhead
        ot_trailhead = {
            "properties": {
              "name" : trailhead['properties']['Name'],
              "trailIds" : get_trail_ids(trailhead['properties']),
              "stewardId" : None,
              "areaId" : None,
              "address" : get_address(trailhead['properties']),
              "parking" : yes_or_no(trailhead['properties']['parking']),
              "drinkwater" : yes_or_no(trailhead['properties']['drinkwater']),
              "restrooms" : yes_or_no(trailhead['properties']['restrooms']),
              "kiosk" : yes_or_no(trailhead['properties']['kiosk']),
              "osmTags" : "natural=stone; natural=tree"
            },
            "geometry" : trailhead['geometry']
        }

        ot_data['features'].append(ot_trailhead)
    return ot_data



@app.route('/', methods=['GET', 'POST'])
def upload_file():
    # Show an uplaod form or process an uploaded file
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            shapefile_path = unzipfile('uploads/'+filename)
            geojson_path = shp2geojson(shapefile_path)
            data = open_geojson(geojson_path)
            namedtrails = create_namedtrails(data)
            write_namedtrails(namedtrails)
            # ot_data = convert2open_trails(data)
            return json.dumps(data, sort_keys=True)

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
