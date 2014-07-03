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

def segments_transform(raw_geojson, dataset):
    ''' Return progress messages and a new GeoJSON structure.
    
        Guess standard fields from properties.
    '''
    messages = []
    opentrails_geojson = {'type': 'FeatureCollection', 'features': []}
    id_counter = itertools.count(1)

    for old_segment in raw_geojson['features']:
        old_properties = old_segment['properties']
    
        new_segment = {
         "type" : "Feature",
         "geometry" : old_segment['geometry'],
         "properties" : {
             "id" : find_segment_id(messages, old_properties) or str(id_counter.next()),
             "stewardId" : None,
             "name" : find_segment_name(messages, old_properties),
             "motor_vehicles" : find_segment_motor_vehicles_use(messages, old_properties),
             "foot" : find_segment_foot_use(messages, old_properties),
             "bicycle" : find_segment_bicycle_use(messages, old_properties),
             "horse" : find_segment_horse_use(messages, old_properties),
             "ski" : find_segment_ski_use(messages, old_properties),
             "wheelchair" : find_segment_wheelchair_use(messages, old_properties),
             "osmTags" : None
         }
        }
        opentrails_geojson['features'].append(new_segment)

    deduped_messages = []
    
    for message in messages:
        if message not in deduped_messages:
            deduped_messages.append(message)
    
    return deduped_messages, opentrails_geojson

def find_segment_id(messages, properties):
    ''' Return the value of a unique segment identifier from feature properties.
    
        Implements logic in https://github.com/codeforamerica/PLATS/issues/26
        
        Gather messages along the way about potential problems.
    '''
    keys, values = zip(*[(k.lower(), v) for (k, v) in properties.items()])
    
    for field in ('id', 'trailid', 'objectid', 'trail id', 'object id'):
        if field in keys:
            return values[keys.index(field)]
    
    messages.append(('warning', 'No column found for trail ID, such as "id" or "trailid". A new numeric ID was created.'))
    
    return None

def find_segment_name(messages, properties):
    ''' Return the value of a segment name from feature properties.
    
        Implements logic in https://github.com/codeforamerica/PLATS/issues/35
        
        Gather messages along the way about potential problems.
    '''
    keys, values = zip(*[(k.lower(), v) for (k, v) in properties.items()])
    
    for field in ('name', 'trail', 'trailname', 'trail name', 'trail_name'):
        if field in keys:
            return values[keys.index(field)]
    
    messages.append(('error', 'No column found for trail name, such as "name" or "trail".'))
    
    return None

def _has_listed_field(properties, fieldnames):
    ''' Return true if properties has one of the case-insensitive field names.
    '''
    keys = [k.lower() for k in properties.keys()]

    for field in fieldnames:
        if field.lower() in keys:
            return True
    
    return False

def _get_value_yes_no(properties, fieldnames):
    ''' Return yes/no value for one of the case-insensitive field names.
    '''
    yes_nos = {'y': 'yes', 'yes': 'yes', 'n': 'no', 'no': 'no'}
    
    keys, values = zip(*[(k.lower(), v) for (k, v) in properties.items()])

    for field in fieldnames:
        if field.lower() in keys:
            value = values[keys.index(field)]
            return value and yes_nos.get(value.lower(), None)
    
    return None

def _get_match_yes_no(properties, pattern, fieldnames):
    ''' Return yes/no value for pattern match on one of the case-insensitive field names.
    '''
    keys, values = zip(*[(k.lower(), v) for (k, v) in properties.items()])

    for field in fieldnames:
        if field.lower() in keys:
            value = values[keys.index(field)]
            
            if type(value) not in (str, unicode):
                return None
            
            return pattern.search(value) and 'yes' or 'no'
    
    return None

def find_segment_foot_use(messages, properties):
    ''' Return the value of a segment foot use flag from feature properties.
    
        Implements logic in https://github.com/codeforamerica/PLATS/issues/28
        
        Gather messages along the way about potential problems.
    '''
    # Search for a hike column
    fieldnames = 'hike', 'walk', 'foot'
    
    if _has_listed_field(properties, fieldnames):
        return _get_value_yes_no(properties, fieldnames)

    # Search for a use column and look for hiking inside
    fieldnames = 'use', 'use_type', 'pubuse'
    pattern = re.compile(r'\b(?<!no )(multi-use|hike|foot|hiking|walk|walking)\b', re.I)
    
    if _has_listed_field(properties, fieldnames):
        return _get_match_yes_no(properties, pattern, fieldnames)
            
    messages.append(('warning', 'No column found for foot use, such as "hike" or "walk". Leaving "foot" blank.'))
    
    return None

def find_segment_bicycle_use(messages, properties):
    ''' Return the value of a segment bicycle use flag from feature properties.
    
        Implements logic in https://github.com/codeforamerica/PLATS/issues/29
        
        Gather messages along the way about potential problems.
    '''
    # Search for a bicycle column
    fieldnames = 'bike', 'roadbike', 'bikes', 'road bike', 'mtnbike'
    
    if _has_listed_field(properties, fieldnames):
        return _get_value_yes_no(properties, fieldnames)

    # Search for a use column and look for biking inside
    fieldnames = 'use', 'use_type', 'pubuse'
    pattern = re.compile(r'\b(?<!no )(multi-use|bike|bikes|roadbike|road bike|bicycles|bicycling|bicycling)\b', re.I)
    
    if _has_listed_field(properties, fieldnames):
        return _get_match_yes_no(properties, pattern, fieldnames)
            
    messages.append(('warning', 'No column found for bicycle use, such as "bikes" or "road bike". Leaving "bicycle" blank.'))
            
    return None

def find_segment_horse_use(messages, properties):
    ''' Return the value of a segment horse use flag from feature properties.
    
        Implements logic in https://github.com/codeforamerica/PLATS/issues/30
        
        Gather messages along the way about potential problems.
    '''
    # Search for a horse column
    fieldnames = 'horse', 'horses', 'equestrian'
    
    if _has_listed_field(properties, fieldnames):
        return _get_value_yes_no(properties, fieldnames)

    # Search for a use column and look for horsies inside
    fieldnames = 'use', 'use_type', 'pubuse'
    pattern = re.compile(r'\b(?<!no )(horse|horses|equestrian|horseback)\b', re.I)
    
    if _has_listed_field(properties, fieldnames):
        return _get_match_yes_no(properties, pattern, fieldnames)
            
    messages.append(('warning', 'No column found for horse use, such as "horses", "equestrian", etc. Leaving "horse" blank.'))
            
    return None

def find_segment_ski_use(messages, properties):
    ''' Return the value of a segment ski use flag from feature properties.
    
        Implements logic in https://github.com/codeforamerica/PLATS/issues/31
        
        Gather messages along the way about potential problems.
    '''
    # Search for a ski column
    fieldnames = 'ski', 'XCntrySki', 'CROSSCSKI'
    
    if _has_listed_field(properties, fieldnames):
        return _get_value_yes_no(properties, fieldnames)

    # Search for a use column and look for skis inside
    fieldnames = 'use', 'use_type', 'pubuse'
    pattern = re.compile(r'\b(?<!no )(ski|xcntryski|skiing|countryski|crosscountryski|multi-use)\b', re.I)
    
    if _has_listed_field(properties, fieldnames):
        return _get_match_yes_no(properties, pattern, fieldnames)
            
    messages.append(('warning', 'No column found for ski use, such as "skiing" or "cross country ski". Leaving "ski" blank.'))
            
    return None

def find_segment_wheelchair_use(messages, properties):
    ''' Return the value of a segment wheelchair use flag from feature properties.
    
        Implements logic in https://github.com/codeforamerica/PLATS/issues/32
        
        Gather messages along the way about potential problems.
    '''
    # Search for a wheelchair column
    fieldnames = 'wheelchair', "accessible", "adaaccess", "accesibil", "ada"
    
    if _has_listed_field(properties, fieldnames):
        return _get_value_yes_no(properties, fieldnames)
            
    messages.append(('warning', 'No column found for wheelchair accessibility, such as "accessible" or "ADA". Leaving "wheelchair" blank.'))
            
    return None

def find_segment_motor_vehicles_use(messages, properties):
    ''' Return the value of a segment motor_vehicles use flag from feature properties.
    
        Implements logic in https://github.com/codeforamerica/PLATS/issues/33
        
        Gather messages along the way about potential problems.
    '''
    # Search for a motor_vehicles column
    fieldnames = "MOTORBIKE", "ALLTERVEH", "ATV", "FOURWD", "4WD", "Motorcycle", "Snowmobile"
    
    if _has_listed_field(properties, fieldnames):
        return _get_value_yes_no(properties, fieldnames)
            
    messages.append(('warning', 'No column found for motor vehicle use, such as "motorbike" or "ATV". Leaving "motor_vehicles" blank.'))
            
    return None
