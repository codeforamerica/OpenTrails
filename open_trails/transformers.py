import os, json, subprocess, itertools, re

from .functions import encode_list

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
             "id" : str(find_segment_id(messages, old_properties) or id_counter.next()),
             "steward_id" : "0",
             "name" : find_segment_name(messages, old_properties),
             "motor_vehicles" : find_segment_motor_vehicles_use(messages, old_properties),
             "foot" : find_segment_foot_use(messages, old_properties),
             "bicycle" : find_segment_bicycle_use(messages, old_properties),
             "horse" : find_segment_horse_use(messages, old_properties),
             "ski" : find_segment_ski_use(messages, old_properties),
             "wheelchair" : find_segment_wheelchair_use(messages, old_properties),
             "osm_tags" : None
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

    messages.append(('warning', 'missing-segment-id', 'No column found for trail ID, such as "id" or "trailid". A new numeric ID was created.'))

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

    messages.append(('error', 'missing-segment-name', 'No column found for trail name, such as "name" or "trail".'))

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
            value = values[keys.index(field.lower())]
            return value and yes_nos.get(value.lower(), None)

    return None

def _get_match_yes_no(properties, pattern, fieldnames):
    ''' Return yes/no value for pattern match on one of the case-insensitive field names.
    '''
    keys, values = zip(*[(k.lower(), v) for (k, v) in properties.items()])

    for field in fieldnames:
        if field.lower() in keys:
            value = values[keys.index(field.lower())]

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

    messages.append(('warning', 'missing-segment-foot', 'No column found for foot use, such as "hike" or "walk". Leaving "foot" blank.'))

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

    messages.append(('warning', 'missing-segment-bicycle', 'No column found for bicycle use, such as "bikes" or "road bike". Leaving "bicycle" blank.'))

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

    messages.append(('warning', 'missing-segment-horse', 'No column found for horse use, such as "horses", "equestrian", etc. Leaving "horse" blank.'))

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

    messages.append(('warning', 'missing-segment-ski', 'No column found for ski use, such as "skiing" or "cross country ski". Leaving "ski" blank.'))

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

    messages.append(('warning', 'missing-segment-wheelchair', 'No column found for wheelchair accessibility, such as "accessible" or "ADA". Leaving "wheelchair" blank.'))

    return None

def find_segment_motor_vehicles_use(messages, properties):
    ''' Return the value of a segment motor_vehicles use flag from feature properties.

        Implements logic in https://github.com/codeforamerica/PLATS/issues/33

        Gather messages along the way about potential problems.
    '''
    # Search for a motor_vehicles column
    fieldnames = "MOTORBIKE", "ALLTERVEH", "ATV", "FOURWD", "4WD", "Motorcycle", "Snowmobile"
    #  we recieved one set of data wherein the field name is MOTORBIKE, and the value is 'motorcycle'
    pattern = re.compile(r'\b(?<!no )(motorcylce)\b', re.I)

    if _has_listed_field(properties, fieldnames):
        return _get_value_yes_no(properties, fieldnames)

    messages.append(('warning', 'missing-segment-motor-vehicles', 'No column found for motor vehicle use, such as "motorbike" or "ATV". Leaving "motor_vehicles" blank.'))

    return None

# AJW Code Begins Here

def trailheads_transform(raw_geojson, dataset):
    ''' Return progress messages and a new GeoJSON structure.

        Guess standard fields from properties.

        Pattern replicated from segments_transform
    '''
    messages = []
    opentrails_trailheads_geojson = {'type': 'FeatureCollection', 'features': []}
    id_counter = itertools.count(1)

    for old_trailhead in raw_geojson['features']:
        old_properties = old_trailhead['properties']

        new_trailhead = {
          "type" :  "Feature",
          "geometry" : old_trailhead['geometry'],
          "properties" : {
            "id": str(find_trailhead_id(messages, old_properties) or id_counter.next()),
            "steward_id": "0", # Steward ID 0 is the only steward we generate.
            "name": find_trailhead_name(messages, old_properties),
            "area_id": "0",
            "trail_ids": find_trailhead_trail_ids(messages, old_properties, dataset),
            "address": find_trailhead_address(messages, old_properties),
            "parking": find_trailhead_parking(messages, old_properties),
            "restrooms": find_trailhead_restrooms(messages, old_properties),
            "kiosk": find_trailhead_kiosk(messages, old_properties),
            "drink water": find_trailhead_drinkwater(messages, old_properties),
            "osm_tags": None
          }
        }
        opentrails_trailheads_geojson['features'].append(new_trailhead)

    deduped_messages = []

    for message in messages:
        if message not in deduped_messages:
            deduped_messages.append(message)

    return deduped_messages, opentrails_trailheads_geojson


def find_trailhead_id(messages, properties):
    ''' Return the value of a unique segment identifier from feature properties.

        Implements logic in https://github.com/codeforamerica/PLATS/issues/37

        Gather messages along the way about potential problems.
    '''

    keys, values = zip(*[(k.lower(), v) for (k, v) in properties.items()])

    for field in ('id', 'objectid', 'object id'):
        if field in keys:
            return values[keys.index(field)]

    messages.append(('warning', 'missing-trailhead-id', 'No column found for trailhead ID, such as "id" or "objectid". A new numeric ID was created. '))

    return None

def find_trailhead_name(messages, properties):
    ''' Return the value of a segment name from feature properties.

        Implements logic in https://github.com/codeforamerica/PLATS/issues/36

        Gather messages along the way about potential problems.
    '''

    keys, values = zip(*[(k.lower(), v) for (k, v) in properties.items()])

    for field in ('name', 'thname'):
        if field in keys:
            return values[keys.index(field)]

    messages.append(('error', 'missing-trailhead-name', 'No column found for trail name, such as "name" or "thname".'))

    return None

def find_trailhead_trail_ids(messages, properties, dataset):
    ''' Return the value of a segment name from feature properties.

        Implements logic in https://github.com/codeforamerica/PLATS/issues/39

        Gather messages along the way about potential problems.
    '''

    keys, values = zip(*[(k.lower(), v) for (k, v) in properties.items()])
    
    id_values = list()
    
    for key in keys:
        if key.startswith('trail') or key.startswith('segment'):
            id_values.append(values[keys.index(key)])
    
    if len(id_values):
        return encode_list(id_values)

    messages.append(('error', 'missing-trailhead-trail-ids', 'No column found for trail names, such as "trailname" or "trail1". Trailhead should be associated with at least one trail.'))

    return None

def find_trailhead_address(messages, properties):
    ''' Return the value of a segment name from feature properties.

        Implements logic in https://github.com/codeforamerica/PLATS/issues/41

        Gather messages along the way about potential problems.
    '''

    keys, values = zip(*[(k.lower(), v) for (k, v) in properties.items()])

    for field in ('add', 'addr', 'address', 'street', 'siteaddr'):
        if field in keys:
            return values[keys.index(field)]

    messages.append(('warning', 'missing-trailhead-address', 'No column found for trailhead address, such as "address" or "siteaddr". Leaving "address" blank.'))

    return None

def find_trailhead_parking(messages, properties):
    ''' Return the value of a segment name from feature properties.

        Implements logic in https://github.com/codeforamerica/PLATS/issues/42

        Gather messages along the way about potential problems.
    '''

    keys, values = zip(*[(k.lower(), v) for (k, v) in properties.items()])

    fieldnames = 'park', 'parking', 'parking lot', 'roadside'

    if _has_listed_field(properties, fieldnames):
        return _get_value_yes_no(properties, fieldnames)

    # Search for a parking column and look for parking strings inside
    fieldnames = 'park', 'parking'
    pattern = re.compile(r'\b(?<!no )(parking lot|roadside parking|parking)\b', re.I)

    if _has_listed_field(properties, fieldnames):
        return _get_match_yes_no(properties, pattern, fieldnames)

    messages.append(('warning', 'missing-trailhead-parking', 'No column found for trailhead parking, such as "parking" or "roadside". Leaving "parking" blank.'))

    return None

def find_trailhead_restrooms(messages, properties):
    ''' Return the value of a segment name from feature properties.

        Implements logic in https://github.com/codeforamerica/PLATS/issues/44

        Gather messages along the way about potential problems.
    '''

    fieldnames = 'restroom', 'bathroom', 'toilet'

    if _has_listed_field(properties, fieldnames):
        return _get_value_yes_no(properties, fieldnames)

    messages.append(('warning', 'missing-trailhead-restroom', 'No column found for trailhead restroom, such as "bathroom" or "toilet". Leaving "restroom" blank.'))

    return None

def find_trailhead_kiosk(messages, properties):
    ''' Return the value of a segment name from feature properties.

        Implements logic in https://github.com/codeforamerica/PLATS/issues/45

        Gather messages along the way about potential problems.
    '''


    fieldnames = 'info', 'information', 'kiosk'
    if _has_listed_field(properties, fieldnames):
        return _get_value_yes_no(properties, fieldnames)

    messages.append(('warning', 'missing-trailhead-kiosk', 'No column found for trailhead kiosk, such as "info" or "kiosk". Leaving "kiosk" blank.'))

    return None

def find_trailhead_drinkwater(messages, properties):
    ''' Return the value of a segment name from feature properties.

        Implements logic in https://github.com/codeforamerica/PLATS/issues/43

        Gather messages along the way about potential problems.
    '''

    fieldnames = 'water', 'drinkingwa', 'drinkwater'
    if _has_listed_field(properties, fieldnames):
        return _get_value_yes_no(properties, fieldnames)

    messages.append(('warning', 'missing-trailhead-drinkwater', 'No column found for trailhead drinking water, such as "drinkwater" or "water". Leaving "drinkwater" blank.'))

    return None