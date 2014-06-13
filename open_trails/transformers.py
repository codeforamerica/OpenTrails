import os, json, subprocess

def shp2geojson(filename):
    '''Converts a shapefile to a geojson file with spherical mercator.
    '''
    in_file = filename
    out_file = '{0}.geojson'.format(filename)

    args = 'ogr2ogr -t_srs EPSG:4326  -f GeoJSON ___ ___'.split()
    args[-2:] = out_file, in_file
    if os.path.exists(out_file):
        os.remove(out_file)
    subprocess.check_call(args)
    return out_file

def open_geojson(geojson_path):
    '''Reads a geojson file. Returns a python obj.
    '''
    json_data=open(geojson_path)
    data = json.load(json_data)
    json_data.close()
    return data

def transform_shapefile(shapefile_path):
    '''
    Convert a shp file to a geojson file
    Open geojson file and return it as a python obj.
    '''
    geojson_path = shp2geojson(shapefile_path)
    data = open_geojson(geojson_path)
    return data

def portland_transform(raw_geojson):

    opentrails_geojson = {'type': 'FeatureCollection', 'features': []}

    def bicycle(properties):
        if properties['ROADBIKE'] == 'Yes' or properties['MTNBIKE'] == 'Yes':
            return "yes"
        else:
            return "no"

    def horse(properties):
        if properties['EQUESTRIAN'] == 'Yes':
            return "yes"
        else:
            return "no"

    def wheelchair(properties):
        if properties['ACCESSIBLE'] == 'Yes':
            return "yes"
        else:
            return "no"

    for old_segment in raw_geojson['features']:
        new_segment = {
         "type" : "Feature",
         "geometry" : old_segment['geometry'],
         "properties" : {
             "id" : old_segment['properties']['TRAILID'],
             "stewardId" : old_segment['properties']['AGENCYNAME'],
             "name" : old_segment['properties']['TRAILNAME'],
             "vehicles" : None,
             "foot" : old_segment['properties']['HIKE'].lower(),
             "bicycle" : bicycle(old_segment['properties']),
             "horse" : horse(old_segment['properties']),
             "ski" : None,
             "wheelchair" : wheelchair(old_segment['properties']),
             "osmTags" : None
         }
        }
        opentrails_geojson['features'].append(new_segment)

    return opentrails_geojson

def sa_transform(raw_geojson, steward_id):

    opentrails_geojson = {'type': 'FeatureCollection', 'features': []}

    trailhead_ids = 1
    for old_trailhead in raw_geojson['features']:
        new_trailhead = {
         "type" : "Feature",
         "geometry" : old_trailhead['geometry'],
         "properties" : {
            "name": old_trailhead['properties']['Name'],
            "id": trailhead_ids,
            "trailIds": None,
            "stewardId": steward_id,
            "areaId": None,
            "address": None,
            "parking": None,
            "drinkwater": None,
            "restrooms": None,
            "kiosk": None,
            "osmTags": None
         }
        }
        opentrails_geojson['features'].append(new_trailhead)
        trailhead_ids += 1

    return opentrails_geojson
