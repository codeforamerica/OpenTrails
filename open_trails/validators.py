from os.path import exists

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

def check_trail_segments(messages, path):
    '''
    '''
    pass

def check_named_trails(messages, path):
    '''
    '''
    pass

def check_trailheads(messages, path):
    '''
    '''
    pass

def check_stewards(messages, path):
    '''
    '''
    pass

def check_areas(messages, path):
    '''
    '''
    pass
