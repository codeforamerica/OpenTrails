from os.path import exists, basename
from shapely.geometry import shape
from json import load

class ValidationError (Exception):

    def __init__(self, type, message):
        self.type = type
        self.message = message

def check_open_trails(ts_path, nt_path, th_path, s_path, a_path):
    '''
    '''
    messages = []
    
    if not exists(ts_path):
        messages.append(('error', 'missing-file-trail-segments', 'Could not find required file trail_segments.geojson.'))
    else:
        check_trail_segments(messages, ts_path)
    
    if not exists(nt_path):
        messages.append(('error', 'missing-file-named-trails', 'Could not find required file named_trails.csv.'))
    else:
        check_named_trails(messages, nt_path)
    
    if not exists(th_path):
        messages.append(('error', 'missing-file-trailheads', 'Could not find required file trailheads.geojson.'))
    else:
        check_trailheads(messages, th_path)
    
    if not exists(s_path):
        messages.append(('error', 'missing-file-stewards', 'Could not find required file stewards.csv.'))
    else:
        check_stewards(messages, s_path)
    
    if not exists(a_path):
        messages.append(('warning', 'missing-file-areas', 'Could not find optional file areas.geojson.'))
    else:
        check_areas(messages, a_path)
    
    deduped_messages = []
    passed_validation = True
    
    for message in messages:
        if message not in deduped_messages:
            deduped_messages.append(message)
        
        if message[0] == 'error':
            passed_validation = False
    
    return deduped_messages, passed_validation

_geojson_geometry_types = 'Point', 'LineString', 'MultiLineString', 'Polygon', 'MultiPolygon'

def check_geojson_structure(path, allowed_geometry_types=_geojson_geometry_types):
    ''' Verify core GeoJSON syntax of a file.
    
        Return features list if everything checks out, or raise a ValidationError.
    '''
    name = basename(path)
    
    try:
        data = load(open(path))
    except:
        raise ValidationError('incorrect-geojson-file', 'Could not load required file "{0}".'.format(name))
    
    if data.get('type', None) != 'FeatureCollection':
        raise ValidationError('incorrect-geojson-file', 'Incorrect GeoJSON type in {0}.'.format(name))
    
    if type(data.get('features', None)) is not list:
        raise ValidationError('incorrect-geojson-file', 'Bad features list in {0}.'.format(name))
    
    for feature in data['features']:
        if feature.get('type', None) != 'Feature':
            raise ValidationError('incorrect-geojson-file', 'Incorrect GeoJSON feature type in {0}.'.format(name))

        if type(feature.get('properties', None)) is not dict:
            raise ValidationError('incorrect-geojson-file', 'Incorrect GeoJSON properties type in {0}.'.format(name))

        if type(feature.get('geometry', None)) is not dict:
            raise ValidationError('incorrect-geojson-file', 'Incorrect GeoJSON geometry type in {0}.'.format(name))
        
        if feature['geometry'].get('type', None) not in allowed_geometry_types:
            raise ValidationError('incorrect-geojson-file', 'Incorrect GeoJSON geometry type in {0}.'.format(name))
        
        if type(feature['geometry'].get('coordinates', None)) is not list:
            raise ValidationError('incorrect-geojson-file', 'Incorrect GeoJSON geometry coordinates in {0}.'.format(name))
        
        try:
            shape(feature['geometry'])
        except ValueError, e:
            raise ValidationError('incorrect-geojson-file', 'Unrecognizeable GeoJSON geometry in {0}.'.format(name))
    
    return data['features']

def _check_required_string_field(messages, field, properties, table_name):
    ''' Find and note missing or badly-typed required string fields.
    '''
    message_type = 'bad-data-' + table_name.replace(' ', '-')
    title_name = table_name[0].upper() + table_name[1:]
    
    if field not in properties:
        message_text = 'Required {0} field "{1}" is missing.'.format(table_name, field)
        messages.append(('error', message_type, message_text))

    elif type(properties[field]) not in (str, unicode):
        found_type = type(properties[field])
        message_text = '{0} "{1}" field is the wrong type: {2}.'.format(title_name, field, repr(found_type))
        messages.append(('error', message_type, message_text))

def _check_optional_string_field(messages, field, properties, table_name):
    ''' Find and note missing or badly-typed optional string fields.
    '''
    message_type = 'bad-data-' + table_name.replace(' ', '-')
    title_name = table_name[0].upper() + table_name[1:]
    
    if field not in properties:
        message_text = 'Optional {0} field "{1}" is missing.'.format(table_name, field)
        messages.append(('warning', message_type, message_text))

    elif type(properties[field]) not in (str, unicode, type(None)):
        found_type = type(properties[field])
        message_text = '{0} "{1}" field is the wrong type: {2}.'.format(title_name, field, repr(found_type))
        messages.append(('error', message_type, message_text))

def _check_optional_boolean_field(messages, field, properties, table_name):
    ''' Find and note missing or badly-typed optional boolean fields.
    '''
    message_type = 'bad-data-' + table_name.replace(' ', '-')
    title_name = table_name[0].upper() + table_name[1:]
    
    if field not in properties:
        message_text = 'Optional {0} field "{1}" is missing.'.format(table_name, field)
        messages.append(('warning', message_type, message_text))

    elif properties[field] not in ('yes', 'no', None):
        found_value = properties[field]
        message_text = '{0} "{1}" field is not an allowed value: {2}.'.format(title_name, field, repr(found_value))
        messages.append(('error', message_type, message_text))

def check_trail_segments(messages, path):
    '''
    '''
    try:
        features = check_geojson_structure(path, ('LineString', 'MultiLineString'))
    except ValidationError, e:
        messages.append(('error', e.type, e.message))
    
    for feature in features:
        properties = feature['properties']
        
        for field in ('id', 'steward_id'):
            _check_required_string_field(messages, field, properties, 'trail segments')

        _check_optional_string_field(messages, 'name', properties, 'trail segments')
        
        for field in ('motor_vehicles', 'foot', 'bicycle', 'horse', 'ski', 'wheelchair'):
            _check_optional_boolean_field(messages, field, properties, 'trail segments')

def check_named_trails(messages, path):
    '''
    '''
    pass

def check_trailheads(messages, path):
    '''
    '''
    try:
        features = check_geojson_structure(path, ('Point', ))
    except ValidationError, e:
        messages.append(('error', e.type, e.message))
    
    for feature in features:
        properties = feature['properties']
        
        for field in ('name', 'trail_ids', 'steward_ids'):
            _check_required_string_field(messages, field, properties, 'trailheads')

        for field in ('address', ):
            _check_optional_string_field(messages, field, properties, 'trailheads')
        
        for field in ('parking', 'drinkwater', 'restrooms', 'kiosk'):
            _check_optional_boolean_field(messages, field, properties, 'trailheads')

def check_stewards(messages, path):
    '''
    '''
    pass

def check_areas(messages, path):
    '''
    '''
    try:
        features = check_geojson_structure(path, ('Polygon', 'MultiPolygon'))
    except ValidationError, e:
        messages.append(('error', e.type, e.message))
    
    for feature in features:
        properties = feature['properties']
        
        for field in ('name', 'id', 'steward_id'):
            _check_required_string_field(messages, field, properties, 'areas')

        for field in ('url', ):
            _check_optional_string_field(messages, field, properties, 'areas')
