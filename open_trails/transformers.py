import os, json, subprocess, itertools, re

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

def segments_transform(raw_geojson, steward):
    ''' Return a new GeoJSON structure, with standard fields guessed from properties.
    '''
    opentrails_geojson = {'type': 'FeatureCollection', 'features': []}
    id_counter = itertools.count(1)

    for old_segment in raw_geojson['features']:
        old_properties = old_segment['properties']
    
        new_segment = {
         "type" : "Feature",
         "geometry" : old_segment['geometry'],
         "properties" : {
             "id" : find_segment_id(old_properties) or id_counter.next(),
             "stewardId" : None,
             "name" : None,
             "vehicles" : None,
             "foot" : find_segment_foot_use(old_properties),
             "bicycle" : find_segment_bicycle_use(old_properties),
             "horse" : None,
             "ski" : None,
             "wheelchair" : None,
             "osmTags" : None
         }
        }
        opentrails_geojson['features'].append(new_segment)

    return opentrails_geojson

def find_segment_id(properties):
    ''' Return the value of a unique segment identifier from feature properties.
    
        Implements logic in https://github.com/codeforamerica/PLATS/issues/26
    '''
    keys, values = zip(*[(k.lower(), v) for (k, v) in properties.items()])
    
    if 'id' in keys:
        return values[keys.index('id')]
    
    elif 'trailid' in keys:
        return values[keys.index('trailid')]
    
    elif 'objectid' in keys:
        return values[keys.index('objectid')]
    
    return None

def find_segment_foot_use(properties):
    ''' Return the value of a segment foot use flag from feature properties.
    
        Implements logic in https://github.com/codeforamerica/PLATS/issues/28
    '''
    yes_nos = {'y': 'yes', 'yes': 'yes', 'n': 'no', 'no': 'no'}
    
    # Search for a hike column
    keys, values = zip(*[(k.lower(), v) for (k, v) in properties.items()])

    if 'hike' in keys:
        return yes_nos.get(values[keys.index('hike')].lower(), None)
    if 'walk' in keys:
        return yes_nos.get(values[keys.index('walk')].lower(), None)
    if 'foot' in keys:
        return yes_nos.get(values[keys.index('foot')].lower(), None)

    # Search for a use column and look for hiking inside
    pattern = re.compile(r'\b(multi-use|hike|foot|hiking|walk|walking)\b', re.I)

    if 'use' in keys:
        if values[keys.index('use')] is None: return None
        return pattern.search(values[keys.index('use')]) and 'yes' or 'no'
    if 'use_type' in keys:
        if values[keys.index('use_type')] is None: return None
        return pattern.search(values[keys.index('use_type')]) and 'yes' or 'no'
    if 'pubuse' in keys:
        if values[keys.index('pubuse')] is None: return None
        return pattern.search(values[keys.index('pubuse')]) and 'yes' or 'no'
            
    return None

def find_segment_bicycle_use(properties):
    ''' Return the value of a segment bicycle use flag from feature properties.
    
        Implements logic in https://github.com/codeforamerica/PLATS/issues/28
    '''
    yes_nos = {'y': 'yes', 'yes': 'yes', 'n': 'no', 'no': 'no'}
    
    keys, values = zip(*[(k.lower(), v) for (k, v) in properties.items()])

    # Search for a bicycle column
    for bicycle in 'bike', 'roadbike', 'bikes', 'road bike', 'mtnbike':
        if bicycle in keys:
            return yes_nos.get(values[keys.index(bicycle)].lower(), None)

    # Search for a use column and look for biking inside
    pattern = re.compile(r'\b(multi-use|bike|roadbike|bicycling|bicycling)\b', re.I)
    
    for combined in 'use', 'use_type', 'pubuse':
        if combined in keys:
            if values[keys.index(combined)] is None: return None
            return pattern.search(values[keys.index(combined)]) and 'yes' or 'no'
            
    return None

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
