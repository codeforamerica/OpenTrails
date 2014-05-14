import os, os.path, json, subprocess, zipfile
from werkzeug.utils import secure_filename
from open_trails import app

app.config['UPLOAD_FOLDER'] = 'uploads'
ALLOWED_EXTENSIONS = set(['zip'])

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
    in_file = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    out_file = 'uploads/{0}.geojson'.format(filename)

    args = 'ogr2ogr -t_srs EPSG:4326 -f GeoJSON ___ ___'.split()
    args[-2:] = out_file, in_file
    if os.path.exists(out_file):
        os.remove(out_file)
    subprocess.check_call(args)
    return out_file

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

def transform_shapefile(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        shapefile_path = unzipfile(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        geojson_path = shp2geojson(shapefile_path)
        data = open_geojson(geojson_path)
        return data
        # namedtrails = create_namedtrails(data)
        # write_namedtrails(namedtrails)
        # ot_data = convert2open_trails(data)
#
# @app.route('/uploads/<filename>')
# def uploaded_file(filename):
#     return send_from_directory(app.config['UPLOAD_FOLDER'],
#                                filename)
