from os.path import exists, basename
from csv import DictReader
from json import load, dumps

from shapely.geometry import shape

class _VE (Exception):

    def __init__(self, type, message):
        self.type = type
        self.message = message

def check_open_trails(ts_path, nt_path, th_path, s_path, a_path):
    '''
    '''
    msgs = []
    
    if exists(ts_path):
        check_trail_segments(msgs, ts_path)
    else:
        msgs.append(('error', 'missing-file-trail-segments',
                     'Could not find required file trail_segments.geojson.'))
    
    if exists(nt_path):
        check_named_trails(msgs, nt_path)
    else:
        msgs.append(('error', 'missing-file-named-trails',
                     'Could not find required file named_trails.csv.'))
    
    if exists(th_path):
        check_trailheads(msgs, th_path)
    else:
        msgs.append(('error', 'missing-file-trailheads',
                     'Could not find required file trailheads.geojson.'))
    
    if exists(s_path):
        check_stewards(msgs, s_path)
    else:
        msgs.append(('error', 'missing-file-stewards',
                     'Could not find required file stewards.csv.'))
    
    if exists(a_path):
        check_areas(msgs, a_path)
    else:
        msgs.append(('warning', 'missing-file-areas',
                     'Could not find optional file areas.geojson.'))
    
    deduped_messages = []
    passed_validation = True
    
    for message in msgs:
        if message not in deduped_messages:
            deduped_messages.append(message)
        
        if message[0] == 'error':
            passed_validation = False
    
    return deduped_messages, passed_validation

_geojson_geometry_types = 'Point', 'LineString', 'MultiLineString', 'Polygon', 'MultiPolygon'

def check_geojson_structure(path, allowed_geometry_types=_geojson_geometry_types):
    ''' Verify core GeoJSON syntax of a file.
    
        Return features list if everything checks out, or raise a validation error.
    '''
    name = basename(path)
    t = 'incorrect-geojson-file'
    
    try:
        data = load(open(path))
    except:
        raise _VE(t, 'Could not load required file {0}.'.format(name))
    
    if data.get('type', None) != 'FeatureCollection':
        raise _VE(t, 'Incorrect GeoJSON type in {0}.'.format(name))
    
    if type(data.get('features', None)) is not list:
        raise _VE(t, 'Bad features list in {0}.'.format(name))
    
    for feature in data['features']:
        if feature.get('type', None) != 'Feature':
            raise _VE(t, 'Incorrect GeoJSON feature type in {0}.'.format(name))

        if type(feature.get('properties', None)) is not dict:
            raise _VE(t, 'Incorrect GeoJSON properties type in {0}.'.format(name))

        if type(feature.get('geometry', None)) is not dict:
            raise _VE(t, 'Incorrect GeoJSON geometry type in {0}.'.format(name))
        
        if feature['geometry'].get('type', None) not in allowed_geometry_types:
            raise _VE(t, 'Incorrect GeoJSON geometry type in {0}.'.format(name))
        
        try:
            shape(feature['geometry'])
        except ValueError, e:
            raise _VE(t, 'Unrecognizeable GeoJSON geometry in {0}.'.format(name))
    
    return data['features']

def check_csv_structure(path):
    ''' Verify core CSV syntax of a file.
    
        Return rows list if everything checks out, or raise a validation error.
    '''
    name = basename(path)
    
    try:
        rows = list(DictReader(open(path)))
    except:
        raise _VE('incorrect-csv-file', 'Could not load required file "{0}".'.format(name))
    
    return rows

def _check_required_string_field(messages, field, dictionary, table_name):
    ''' Find and note missing or badly-typed required string fields.
    '''
    message_type = 'bad-data-' + table_name.replace(' ', '-')
    title_name = table_name[0].upper() + table_name[1:]
    
    if field not in dictionary:
        message_text = 'Required {0} field "{1}" is missing.'.format(table_name, field)
        messages.append(('error', message_type, message_text))

    elif type(dictionary[field]) not in (str, unicode):
        found_type = type(dictionary[field])
        message_text = '{0} "{1}" field is the wrong type: {2}.'.format(title_name, field, repr(found_type))
        messages.append(('error', message_type, message_text))

def _check_optional_string_field(messages, field, dictionary, table_name):
    ''' Find and note missing or badly-typed optional string fields.
    '''
    message_type = 'bad-data-' + table_name.replace(' ', '-')
    title_name = table_name[0].upper() + table_name[1:]
    
    if field not in dictionary:
        message_text = 'Optional {0} field "{1}" is missing.'.format(table_name, field)
        messages.append(('warning', message_type, message_text))

    elif type(dictionary[field]) not in (str, unicode, type(None)):
        found_type = type(dictionary[field])
        message_text = '{0} "{1}" field is the wrong type: {2}.'.format(title_name, field, repr(found_type))
        messages.append(('error', message_type, message_text))

def _check_required_boolean_field(messages, field, dictionary, table_name):
    ''' Find and note missing or badly-typed required boolean fields.
    '''
    message_type = 'bad-data-' + table_name.replace(' ', '-')
    title_name = table_name[0].upper() + table_name[1:]
    
    if field not in dictionary:
        message_text = 'Optional {0} field "{1}" is missing.'.format(table_name, field)
        messages.append(('error', message_type, message_text))

    else:
        value = dictionary[field].lower() if (dictionary[field] is not None) else None
    
        if value not in ('yes', 'no', None):
            found_value = dictionary[field]
            message_text = '{0} "{1}" field is not an allowed value: {2}.'.format(title_name, field, dumps(found_value))
            messages.append(('error', message_type, message_text))

def _check_optional_boolean_field(messages, field, dictionary, table_name):
    ''' Find and note missing or badly-typed optional boolean fields.
    '''
    message_type = 'bad-data-' + table_name.replace(' ', '-')
    title_name = table_name[0].upper() + table_name[1:]
    
    if field not in dictionary:
        message_text = 'Optional {0} field "{1}" is missing.'.format(table_name, field)
        messages.append(('warning', message_type, message_text))

    else:
        value = dictionary[field].lower() if (dictionary[field] is not None) else None
    
        if value not in ('yes', 'no', None):
            found_value = dictionary[field]
            message_text = '{0} "{1}" field is not an allowed value: {2}.'.format(title_name, field, dumps(found_value))
            messages.append(('error', message_type, message_text))

def check_trail_segments(msgs, path):
    '''
    '''
    starting_count = len(msgs)
    
    try:
        features = check_geojson_structure(path, ('LineString', 'MultiLineString'))
    except _VE, e:
        msgs.append(('error', e.type, e.message))
        return
    
    for feature in features:
        properties = feature['properties']
        
        for f in ('id', 'steward_id'):
            _check_required_string_field(msgs, f, properties, 'trail segments')

        for f in ('osm_tags', ):
            _check_optional_string_field(msgs, f, properties, 'trail segments')
        
        for f in ('motor_vehicles', 'foot', 'bicycle', 'horse', 'ski', 'wheelchair'):
            _check_optional_boolean_field(msgs, f, properties, 'trail segments')
    
    if len(msgs) == starting_count:
        msgs.append(('success', 'valid-file-trail-segments', 'Your trail-segments.geojson file looks good.'))

def check_named_trails(messages, path):
    '''
    '''
    starting_count = len(messages)
    
    try:
        rows = check_csv_structure(path)
    except _VE, e:
        messages.append(('error', e.type, e.message))
        return
    
    for row in rows:
        for field in ('name', 'segment_ids', 'id', 'description'):
            _check_required_string_field(messages, field, row, 'named trails')

        for field in ('part_of', ):
            _check_optional_string_field(messages, field, row, 'named trails')
    
    if len(messages) == starting_count:
        messages.append(('success', 'valid-file-named-trails', 'Your named-trails.csv file looks good.'))

def check_trailheads(msgs, path):
    '''
    '''
    starting_count = len(msgs)
    
    try:
        features = check_geojson_structure(path, ('Point', ))
    except _VE, e:
        msgs.append(('error', e.type, e.message))
        return
    
    for feature in features:
        properties = feature['properties']
        
        for field in ('name', 'steward_id'):
            _check_required_string_field(msgs, field, properties, 'trailheads')

        for field in ('address', 'trail_ids', 'segment_ids', 'area_id', 'osm_tags'):
            _check_optional_string_field(msgs, field, properties, 'trailheads')
        
        for field in ('parking', 'drinkwater', 'restrooms', 'kiosk'):
            _check_optional_boolean_field(msgs, field, properties, 'trailheads')
    
    if len(msgs) == starting_count:
        msgs.append(('success', 'valid-file-trailheads', 'Your trailheads.geojson file looks good.'))

def check_stewards(messages, path):
    '''
    '''
    starting_count = len(messages)
    
    try:
        rows = check_csv_structure(path)
    except _VE, e:
        messages.append(('error', e.type, e.message))
        return
    
    for row in rows:
        for field in ('name', 'id', 'url', 'phone', 'address', 'license'):
            _check_required_string_field(messages, field, row, 'stewards')

        for field in ('publisher', ):
            _check_required_boolean_field(messages, field, row, 'stewards')
    
    if len(messages) == starting_count:
        messages.append(('success', 'valid-file-stewards', 'Your stewards.csv file looks good.'))

def check_areas(messages, path):
    '''
    '''
    starting_count = len(messages)
    
    try:
        features = check_geojson_structure(path, ('Polygon', 'MultiPolygon'))
    except _VE, e:
        messages.append(('error', e.type, e.message))
        return
    
    for feature in features:
        properties = feature['properties']
        
        for field in ('name', 'id', 'steward_id'):
            _check_required_string_field(messages, field, properties, 'areas')

        for field in ('url', 'osm_tags'):
            _check_optional_string_field(messages, field, properties, 'areas')
    
    if len(messages) == starting_count:
        messages.append(('success', 'valid-file-areas', 'Your areas.geojson file looks good.'))
