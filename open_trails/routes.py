from open_trails import app
from models import Dataset, make_datastore
from functions import (
    get_dataset, clean_name, unzip, make_id_from_url, compress, zip_file, allowed_file,
    get_sample_segment_features, make_name_trails, package_opentrails_archive,
    get_sample_trailhead_features, get_sample_transformed_trailhead_features,
    get_sample_transformed_segments_features
    )
from transformers import shapefile2geojson, segments_transform, trailheads_transform
from validators import check_open_trails
from flask import request, render_template, redirect, make_response, send_file
import json, os, csv, zipfile, time, re, shutil, uuid
from StringIO import StringIO
from tempfile import mkdtemp

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/datasets')
def datasets():
    '''
    List out all the datasets that have used opentrails so far
    '''
    datastore = make_datastore(app.config['DATASTORE'])
    datasets_list = datastore.datasets()
    return render_template('datasets_list.html', datasets_list=datasets_list, server_url=request.url_root)

@app.route('/check-dataset', methods=['POST'])
def check_dataset():
    '''
    Create a unique url for this dataset to work under
    Create a folder on S3 using this url
    '''
    # Make a new dataset object
    id = str(uuid.uuid4())
    dataset = Dataset(id)
    dataset.datastore = make_datastore(app.config['DATASTORE'])
    
    # Write a verifying file to prove we created these folders
    validname = os.path.join(dataset.id, 'uploads', '.valid')
    dataset.datastore.write(validname, StringIO(dataset.id))

    return redirect('/checks/' + dataset.id)

@app.route('/new-dataset', methods=['POST'])
def new_dataset():
    '''
    Create a unique url for this dataset to work under
    Create a folder on S3 using this url
    '''
    # Make a new dataset object
    id = str(uuid.uuid4())
    dataset = Dataset(id)
    dataset.datastore = make_datastore(app.config['DATASTORE'])
    
    # Write a verifying file to prove we created these folders
    validname = os.path.join(dataset.id, 'uploads', '.valid')
    dataset.datastore.write(validname, StringIO(dataset.id))

    return redirect('/datasets/' + dataset.id)


@app.route('/datasets/<dataset_id>/upload', methods=['POST'])
def upload(dataset_id):
    '''
    Upload a zip of one shapefile to datastore
    '''
    datastore = make_datastore(app.config['DATASTORE'])

    # Check that they uploaded a .zip file
    if not request.files['file'] or not allowed_file(request.files['file'].filename):
        return make_response("Only .zip files allowed", 403)

    # Upload original file to S3
    zip_file = StringIO(request.files['file'].read())
    zip_path = os.path.join(dataset_id, 'uploads', 'trail-segments.zip')
    datastore.write(zip_path, zip_file)

    # Unzip orginal file
    shapefile_path = unzip(zip_file)

    # Get geojson data from shapefile
    geojson = shapefile2geojson(shapefile_path)

    # Write geojson to file in a temporary directory
    geojson_dir = mkdtemp(prefix='geojson-')
    geojson_base, _ = os.path.splitext(os.path.basename(zip_path))
    geojson_path = os.path.join(geojson_dir, geojson_base + '.geojson')
    
    with open(geojson_path, 'w') as file:
        json.dump(geojson, file, sort_keys=True)
    
    # Compress geojson file
    geojson_zip = StringIO()
    compress(geojson_path, geojson_zip)
    shutil.rmtree(geojson_dir)
    
    # Upload .geojson.zip file to datastore
    zip_base, _ = os.path.splitext(zip_path)
    datastore.write(zip_base + '.geojson.zip', geojson_zip)

    # Show sample data from original file
    return redirect('/datasets/' + dataset_id + "/sample-segment")

@app.route('/datasets/<dataset_id>/sample-segment')
def show_sample_segment(dataset_id):
    '''
    Show an example row of data
    '''
    datastore = make_datastore(app.config['DATASTORE'])
    dataset = get_dataset(datastore, dataset_id)
    if not dataset:
        return make_response("No dataset Found", 404)

    features = get_sample_segment_features(dataset)

    keys = list(sorted(features[0]['properties'].keys()))
    args = dict(dataset=dataset, uploaded_features=features, uploaded_keys=keys)
    return render_template("dataset-02-show-sample-segment.html", **args)

@app.route('/datasets/<dataset_id>/transform-segments', methods=['POST'])
def transform_segments(dataset_id):
    '''
    Grab a zip file off of datastore
    Unzip it
    Transform into opentrails
    Upload
    '''
    datastore = make_datastore(app.config['DATASTORE'])
    dataset = get_dataset(datastore, dataset_id)
    if not dataset:
        return make_response("No Dataset Found", 404)

    # Download the original segments file
    up_segments_name = os.path.join(dataset.id, 'uploads', 'trail-segments.geojson.zip')
    up_segments_zip = datastore.read(up_segments_name)

    # Unzip it
    up_segments_path = unzip(up_segments_zip, '.geojson', [])
    up_segments = json.load(open(up_segments_path))
    messages, ot_segments = segments_transform(up_segments, dataset)

    # Save messages for output
    transform_messages_path = dataset.id + "/opentrails/segments-messages.json"
    datastore.write(transform_messages_path, StringIO(json.dumps(messages)))

    # Make a zip from transformed segments
    ot_segments_zip = StringIO()
    ot_segments_raw = json.dumps(ot_segments, sort_keys=True)
    zip_file(ot_segments_zip, ot_segments_raw, 'segments.geojson')

    # Upload transformed segments and messages
    zip_path = os.path.join(dataset.id, 'opentrails', 'segments.geojson.zip')
    datastore.write(zip_path, ot_segments_zip)

    return redirect('/datasets/' + dataset.id + '/transformed-segments', code=303)

@app.route('/datasets/<dataset_id>/transformed-segments')
def transformed_segments(dataset_id):
    datastore = make_datastore(app.config['DATASTORE'])
    dataset = get_dataset(datastore, dataset_id)
    if not dataset:
        return make_response("No Dataset Found", 404)

    # Download the original segments file
    uploaded_features = get_sample_segment_features(dataset)
    uploaded_keys = list(sorted(uploaded_features[0]['properties'].keys()))

    # Download the transformed segments file
    transformed_features = get_sample_transformed_segments_features(dataset)
    transformed_keys = list(sorted(transformed_features[0]['properties'].keys()))

    # Download the transformed segments messages file
    transformed_segments_messages = dataset.id + '/opentrails/segments-messages.json'
    data = json.load(datastore.read(transformed_segments_messages))

    try:
        messages = [(type, id, words) for (type, id, words) in data]
    except ValueError:
        # Old stored format.
        messages = [(type, None, words) for (type, words) in data]

    message_types = [message[0] for message in messages]

    vars = dict(
        dataset = dataset,
        messages = messages,
        uploaded_keys = uploaded_keys,
        uploaded_features = uploaded_features,
        transformed_features = transformed_features,
        transformed_keys = transformed_keys,
        transform_succeeded = bool('error' not in message_types)
        )

    return render_template('dataset-03-transformed-segments.html', **vars)

@app.route('/datasets/<dataset_id>/name-trails', methods=['POST'])
def name_trails(dataset_id):
    datastore = make_datastore(app.config['DATASTORE'])
    dataset = get_dataset(datastore, dataset_id)
    if not dataset:
        return make_response("No Dataset Found", 404)

    # Download the transformed segments file
    transformed_segments_path = os.path.join(dataset.id, 'opentrails', 'segments.geojson.zip')
    transformed_segments_zip = datastore.read(transformed_segments_path)

    # Unzip it
    segments_path = unzip(transformed_segments_zip, '.geojson', [])
    transformed_segments = json.load(open(segments_path))

    # Generate a list of (name, ids) tuples
    named_trails = make_name_trails(transformed_segments['features'])
    
    file = StringIO()
    cols = 'id', 'name', 'segment_ids', 'description', 'part_of'
    writer = csv.writer(file)
    writer.writerow(cols)
    for row in named_trails:
        writer.writerow([(row[c] or '').encode('utf8') for c in cols])

    named_trails_path = os.path.join(dataset.id, 'opentrails', 'named_trails.csv')
    datastore.write(named_trails_path, file)

    return redirect('/datasets/' + dataset.id + '/named-trails', code=303)

@app.route('/datasets/<dataset_id>/named-trails')
def named_trails(dataset_id):
    datastore = make_datastore(app.config['DATASTORE'])
    dataset = get_dataset(datastore, dataset_id)
    if not dataset:
        return make_response("No Dataset Found", 404)

    return render_template('dataset-04-named-trails.html', dataset=dataset)

@app.route('/datasets/<dataset_id>/create-steward', methods=['POST'])
def create_steward(dataset_id):
    datastore = make_datastore(app.config['DATASTORE'])
    dataset = get_dataset(datastore, dataset_id)
    if not dataset:
        return make_response("No Dataset Found", 404)

    steward_fields = 'name', 'id', 'url', 'phone', 'address', 'publisher', 'license'
    steward_values = [request.form.get(f, None) for f in steward_fields]

    steward_values[steward_fields.index('id')] = '0' # This is assigned in segments_transform()
    steward_values[steward_fields.index('publisher')] = 'no' # Better safe than sorry
    
    file = StringIO()
    cols = 'id', 'name', 'segment_ids', 'description', 'part_of'
    writer = csv.writer(file)
    writer.writerow(steward_fields)
    writer.writerow([(v or '').encode('utf8') for v in steward_values])
    
    stewards_path = os.path.join(dataset.id, 'opentrails', 'stewards.csv')
    datastore.write(stewards_path, file)

    return redirect('/datasets/' + dataset.id + '/stewards', code=303)

@app.route('/datasets/<dataset_id>/stewards')
def view_stewards(dataset_id):
    datastore = make_datastore(app.config['DATASTORE'])
    dataset = get_dataset(datastore, dataset_id)
    if not dataset:
        return make_response("No Dataset Found", 404)

    return render_template('dataset-05-stewards.html', dataset=dataset)

@app.route('/datasets/<dataset_id>/no-trailheads', methods=['POST', 'GET'])
def no_trailheads(dataset_id):
    datastore = make_datastore(app.config['DATASTORE'])
    dataset = get_dataset(datastore, dataset_id)
    if not dataset:
        return make_response("No Dataset Found", 404)
    return render_template('dataset-06-no-trailheads.html', dataset=dataset)

@app.route('/datasets/<dataset_id>/upload-trailheads', methods=['POST'])
def upload_trailheads(dataset_id):
    '''
    Upload a zip of one shapefile to datastore
    '''
    datastore = make_datastore(app.config['DATASTORE'])

    # Check that they uploaded a .zip file
    if not request.files['file'] or not allowed_file(request.files['file'].filename):
        return make_response("Only .zip files allowed", 403)

    # Upload original file to S3
    zip_buff = StringIO(request.files['file'].read())
    zip_base = os.path.join(dataset_id, 'uploads', 'trail-trailheads')
    datastore.write(zip_base + '.zip', zip_buff)

    # Get geojson data from shapefile
    shapefile_path = unzip(zip_buff)
    geojson_obj = shapefile2geojson(shapefile_path)

    # Compress geojson file
    geojson_zip = StringIO()
    geojson_raw = json.dumps(geojson_obj)
    zip_file(geojson_zip, geojson_raw, 'trail-trailheads.geojson')
    
    # Upload .geojson.zip file to datastore
    datastore.write(zip_base + '.geojson.zip', geojson_zip)

    # Show sample data from original file
    return redirect('/datasets/' + dataset_id + "/sample-trailhead")

@app.route('/datasets/<dataset_id>/sample-trailhead')
def show_sample_trailhead(dataset_id):
    '''
    Show an example row of data
    '''
    datastore = make_datastore(app.config['DATASTORE'])
    dataset = get_dataset(datastore, dataset_id)
    if not dataset:
        return make_response("No dataset Found", 404)

    features = get_sample_trailhead_features(dataset)

    keys = list(sorted(features[0]['properties'].keys()))
    args = dict(dataset=dataset, uploaded_features=features, uploaded_keys=keys)
    return render_template("dataset-07-show-sample-trailhead.html", **args)

@app.route('/datasets/<dataset_id>/transform-trailheads', methods=['POST'])
def transform_trailheads(dataset_id):
    '''
    Grab a zip file off of datastore
    Unzip it
    Transform into opentrails
    Upload
    '''
    datastore = make_datastore(app.config['DATASTORE'])
    dataset = get_dataset(datastore, dataset_id)
    if not dataset:
        return make_response("No Dataset Found", 404)

    # Download the original trailheads file
    up_trailheads_name = os.path.join(dataset.id, 'uploads', 'trail-trailheads.geojson.zip')
    up_trailheads_zip = datastore.read(up_trailheads_name)

    # Unzip it
    up_trailheads_path = unzip(up_trailheads_zip, '.geojson', [])
    up_trailheads = json.load(open(up_trailheads_path))
    messages, ot_trailheads = trailheads_transform(up_trailheads, dataset)

    # Save messages for output
    transform_messages_path = dataset.id + "/opentrails/trailheads-messages.json"
    datastore.write(transform_messages_path, StringIO(json.dumps(messages)))

    # Make a zip from transformed trailheads
    ot_trailheads_zip = StringIO()
    ot_trailheads_raw = json.dumps(ot_trailheads, sort_keys=True)
    zip_file(ot_trailheads_zip, ot_trailheads_raw, 'trailheads.geojson')

    # Upload transformed trailheads and messages
    zip_path = os.path.join(dataset.id, 'opentrails', 'trailheads.geojson.zip')
    datastore.write(zip_path, ot_trailheads_zip)

    return redirect('/datasets/' + dataset.id + '/transformed-trailheads', code=303)

@app.route('/datasets/<dataset_id>/transformed-trailheads')
def transformed_trailheads(dataset_id):
    datastore = make_datastore(app.config['DATASTORE'])
    dataset = get_dataset(datastore, dataset_id)
    if not dataset:
        return make_response("No Dataset Found", 404)

    # Download the original trailheads file
    uploaded_features = get_sample_trailhead_features(dataset)
    uploaded_keys = list(sorted(uploaded_features[0]['properties'].keys()))

    # Download the transformed trailheads file
    transformed_features = get_sample_transformed_trailhead_features(dataset)
    transformed_keys = list(sorted(transformed_features[0]['properties'].keys()))

    # Download the transformed trailheads messages file
    messages_path = os.path.join(dataset.id, 'opentrails', 'trailheads-messages.json')
    data = json.load(datastore.read(messages_path))

    try:
        messages = [(type, id, words) for (type, id, words) in data]
    except ValueError:
        # Old stored format.
        messages = [(type, None, words) for (type, words) in data]

    message_types = [message[0] for message in messages]

    vars = dict(
        dataset = dataset,
        messages = messages,
        uploaded_keys = uploaded_keys,
        uploaded_features = uploaded_features,
        transformed_features = transformed_features,
        transformed_keys = transformed_keys,
        transform_succeeded = bool('error' not in message_types)
        )

    return render_template('dataset-08-transformed-trailheads.html', **vars)

@app.route('/datasets/<dataset_id>/open-trails.zip')
def download_opentrails_data(dataset_id):
    datastore = make_datastore(app.config['DATASTORE'])
    dataset = get_dataset(datastore, dataset_id)
    if not dataset:
        return make_response("No Dataset Found", 404)

    buffer = package_opentrails_archive(dataset)

    return send_file(buffer, 'application/zip')

@app.route('/datasets/<id>/')
def existing_dataset(id):
    '''
    Reads available files on S3 to figure out how far a dataset has gotten in the process
    '''

    # Init some variable
    # sample_segment, opentrails_sample_segment = False, False

    datastore = make_datastore(app.config['DATASTORE'])
    dataset = get_dataset(datastore, id)
    if not dataset:
        return make_response("No dataset Found", 404)

    # return render_template('index.html', steward = steward, sample_segment = sample_segment, opentrails_sample_segment = opentrails_sample_segment)
    return render_template('dataset-01-upload-segments.html', dataset=dataset)

@app.route('/checks/<id>/')
def existing_validation(id):
    '''
    '''
    datastore = make_datastore(app.config['DATASTORE'])
    dataset = get_dataset(datastore, id)
    if not dataset:
        return make_response("No dataset Found", 404)

    return render_template('check-01-upload-opentrails.html', dataset=dataset)

@app.route('/checks/<dataset_id>/upload', methods=['POST'])
def validate_upload(dataset_id):
    ''' 
    '''
    datastore = make_datastore(app.config['DATASTORE'])

    # Check that they uploaded a .zip file
    if not request.files['file'] or not allowed_file(request.files['file'].filename):
        return make_response("Only .zip files allowed", 403)
        
    upload_dir = os.path.join(dataset_id, 'uploads')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    opentrails_dir = os.path.join(dataset_id, 'opentrails')
    if not os.path.exists(opentrails_dir):
        os.makedirs(opentrails_dir)

    # Read zip data to buffer
    zipfile_data = StringIO()
    zipfile_path = os.path.join(upload_dir, 'open-trails.zip')
    request.files['file'].save(zipfile_data)

    # Upload original file data to S3
    datastore.write(zipfile_path, zipfile_data)

    #
    zf = zipfile.ZipFile(zipfile_data, 'r')
    dirname = os.path.dirname(zipfile_path)
    shapefile_path = None

    names = ['trail_segments.geojson', 'named_trails.csv',
             'trailheads.geojson', 'stewards.csv', 'areas.geojson']

    for name in sorted(zf.namelist()):
        base, (_, ext) = os.path.basename(name), os.path.splitext(name)

        if base in names:
            with open(os.path.join(upload_dir, base), 'w') as file:
                file.write(zf.open(name).read())

    args = [os.path.join(upload_dir, base) for base in names]
    messages, succeeded = check_open_trails(*args)
    
    # Clean up after ourselves.
    shutil.rmtree(dataset_id)
    
    path = os.path.join(opentrails_dir, 'validate-messages.json')
    datastore.write(path, StringIO(json.dumps(messages)))

    # Show sample data from original file
    return redirect('/checks/' + dataset_id + "/results", code=303)

@app.route('/checks/<dataset_id>/results')
def validated_results(dataset_id):
    ''' 
    '''
    datastore = make_datastore(app.config['DATASTORE'])
    dataset = get_dataset(datastore, dataset_id)
    if not dataset:
        return make_response("No dataset Found", 404)

    path = os.path.join(dataset.id, 'opentrails', 'validate-messages.json')
    messages = map(tuple, json.load(datastore.read(path)))
    
    return render_template('check-02-validated-opentrails.html', messages=messages)

@app.route('/errors/<error_id>')
def get_error(error_id):
    return render_template('error-{0}.html'.format(error_id))

### Engine Light - http://engine-light.codeforamerica.org/
@app.route('/.well-known/status', methods=['GET'])
def status():
    response = {}
    response['status'] = 'ok'
    response["updated"] = int(time.time())
    response["dependencies"] = ["S3"]

    # Connect to S3
    try:
      datastore = make_datastore(app.config['DATASTORE'])
    except AttributeError:
      response['status'] = 'Can\'t parse S3 auth'
      response = make_response(json.dumps(response), 403)
      return response

    if not datastore.bucket:
      response['status'] = 'Can\'t connect to S3'
      response = make_response(json.dumps(response), 403)
      return response

    response = make_response(json.dumps(response), 200)
    return response
