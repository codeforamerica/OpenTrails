import os, json, subprocess

def shapefile2geojson(shapefilepath):
    '''Converts a shapefile to a geojson file with spherical mercator.
    '''
    geojsonfilepath = '{0}.geojson'.format(shapefilepath)

    args = 'ogr2ogr -t_srs EPSG:4326  -f GeoJSON ___ ___'.split()
    args[-2:] = geojsonfilepath, shapefilepath
    if os.path.exists(geojsonfilepath):
        os.remove(geojsonfilepath)
    subprocess.check_call(args)
    geojson_data = open(geojsonfilepath)
    geojson = json.load(geojson_data)
    geojson_data.close()
    return geojson

def segments_transform(raw_geosjon, steward):
    try:
        return portland_transform(raw_geojson)
    except:
        pass
    try:
        return sa_transform(raw_geojson, steward.id)
    except:
        pass

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
    import pdb; pdb.set_trace()

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
