from open_trails import app
from models import Dataset, make_datastore
from functions import (
    get_dataset, clean_name, unzip, make_id_from_url, compress, allowed_file,
    get_sample_segment_features, make_name_trails, package_opentrails_archive,
    get_sample_trailhead_features
    )
from transformers import shapefile2geojson, segments_transform, trailheads_transform
from validators import check_open_trails
from flask import request, render_template, redirect, make_response, send_file
import json, os, csv, zipfile, time, re, shutil

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
    '''
    '''
    Create a unique url for this dataset to work under
    Create a folder on S3 using this url
    '''
    # Create uuid
    import uuid
    id = str(uuid.uuid4())

    # Make a new dataset object
    dataset = Dataset(id)
    dataset.datastore = make_datastore(app.config['DATASTORE'])
    
    # Make local folders for dataset
    try:
        os.makedirs(dataset.id + "/uploads")
        os.makedirs(dataset.id + "/opentrails")
    except OSError:
        pass

    # Write a verifying file to prove we created these folders
    with open(os.path.join(dataset.id, 'uploads', '.valid'), "w") as validfile:
        validfile.write(dataset.id)

    # # Upload .valid to datastore
    dataset.datastore.upload(os.path.join(dataset.id, 'uploads', '.valid'))
    return redirect('/checks/' + dataset.id)

@app.route('/new-dataset', methods=['POST'])
def new_dataset():
    '''
    Create a unique url for this dataset to work under
    Create a folder on S3 using this url
    '''

    # Get info from form
    # name, url = request.form['name'], request.form['url']
    # id = make_id_from_url(url)

    # Create uuid
    import uuid
    id = str(uuid.uuid4())

    # Make a new dataset object
    # dataset_info = {"id":id, "name":name, "url":url, "phone":None, "address":None, "publisher":"yes"}
    dataset = Dataset(id)
    dataset.datastore = make_datastore(app.config['DATASTORE'])
    
    # Make local folders for dataset
    try:
        os.makedirs(dataset.id + "/uploads")
        os.makedirs(dataset.id + "/opentrails")
    except OSError:
        pass

    # Write a verifying file to prove we created these folders
    with open(os.path.join(dataset.id, 'uploads', '.valid'), "w") as validfile:
        validfile.write(dataset.id)

    # # Write a stewards.csv file
    # stewards_info_filepath = os.path.join(steward.id, 'uploads', 'stewards.csv')
    # with open(stewards_info_filepath, 'w') as csvfile:
    #     writer = csv.writer(csvfile)
    #     writer.writerow(["name","id","url","phone","address","publisher"])
    #     writer.writerow([steward.name,steward.id,steward.url,steward.phone,steward.address,steward.publisher])
    
    # # Upload .valid to datastore
    dataset.datastore.upload(os.path.join(dataset.id, 'uploads', '.valid'))
    return redirect('/datasets/' + dataset.id)


@app.route('/datasets/<dataset_id>/upload', methods=['POST'])
def upload(dataset_id):
    '''
    Upload a zip of one shapefile to datastore
    '''
    datastore = make_datastore(app.config['DATASTORE'])

    # Check that they uploaded a .zip file
    if request.files['file'] and allowed_file(request.files['file'].filename):
        
        # Save zip file to disk
        # /blahblahblah/uploads/trail-segments.zip
        upload_dir = os.path.join(dataset_id, 'uploads')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        zipfilepath = os.path.join(upload_dir, 'trail-segments.zip')
        request.files['file'].save(zipfilepath)

        # Upload original file to S3
        datastore.upload(zipfilepath)

        # Unzip orginal file
        shapefilepath = unzip(zipfilepath)

        # Get geojson data from shapefile
        geojson = shapefile2geojson(shapefilepath)

        # Write original geojson to file
        geojsonfilepath = zipfilepath.replace('.zip', '.geojson')
        geojsonfile = open(geojsonfilepath,'w')
        geojsonfile.write(json.dumps(geojson, sort_keys=True))
        geojsonfile.close()

        # Compress geojson file
        compress(geojsonfilepath, geojsonfilepath + ".zip")

        # Upload .geojson.zip file to datastore
        datastore.upload(geojsonfilepath + ".zip")
        
        # Clean up after ourselves.
        shutil.rmtree(dataset_id)

        # Show sample data from original file
        return redirect('/datasets/' + dataset_id + "/sample-segment")

    else:
        return make_response("Only .zip files allowed", 403)

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
    
    # Clean up after ourselves.
    shutil.rmtree(dataset.id)

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
    upload_dir = os.path.join(dataset.id, 'uploads')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    segments_zip = os.path.join(upload_dir, 'trail-segments.geojson.zip')
    datastore.download(segments_zip)

    # Unzip it
    segments_path = unzip(segments_zip, '.geojson', [])
    original_segments = json.load(open(segments_path))
    messages, opentrails_segments = segments_transform(original_segments, dataset)

    # Write files from transformed segments
    opentrails_dir = os.path.join(dataset.id, 'opentrails')
    if not os.path.exists(opentrails_dir):
        os.makedirs(opentrails_dir)
    opentrails_segments_path = os.path.join(opentrails_dir, 'segments.geojson')
    opentrails_segments_file = open(opentrails_segments_path ,'w')
    opentrails_segments_file.write(json.dumps(opentrails_segments, sort_keys=True))
    opentrails_segments_file.close()
    
    transform_messages_path = dataset.id + "/opentrails/segments-messages.json"
    with open(transform_messages_path, 'w') as file:
        json.dump(messages, file)

    # zip up transformed segments
    compress(opentrails_segments_path, opentrails_segments_path + ".zip")

    # Upload transformed segments and messages
    datastore.upload(opentrails_segments_path + ".zip")
    datastore.upload(transform_messages_path)
    
    # Clean up after ourselves.
    shutil.rmtree(dataset.id)

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
    opentrails_dir = os.path.join(dataset.id, 'opentrails')
    if not os.path.exists(opentrails_dir):
        os.makedirs(opentrails_dir)
    transformed_segments_zip = os.path.join(opentrails_dir, 'segments.geojson.zip')
    datastore.download(transformed_segments_zip)

    # Unzip it
    segments_path = unzip(transformed_segments_zip, '.geojson', [])
    transformed_segments = json.load(open(segments_path))
    transformed_features = transformed_segments['features'][:3]
    transformed_keys = list(sorted(transformed_features[0]['properties'].keys()))
    
    # Download the transformed segments messages file
    transformed_segments_messages = dataset.id + '/opentrails/segments-messages.json'
    datastore.download(transformed_segments_messages)
    
    with open(transformed_segments_messages) as f:
        data = json.load(f)
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
    
    # Clean up after ourselves.
    shutil.rmtree(dataset.id)

    return render_template('dataset-03-transformed-segments.html', **vars)
        
@app.route('/datasets/<dataset_id>/name-trails', methods=['POST'])
def name_trails(dataset_id):
    datastore = make_datastore(app.config['DATASTORE'])
    dataset = get_dataset(datastore, dataset_id)
    if not dataset:
        return make_response("No Dataset Found", 404)

    # Download the transformed segments file
    opentrails_dir = os.path.join(dataset.id, 'opentrails')
    if not os.path.exists(opentrails_dir):
        os.makedirs(opentrails_dir)
    transformed_segments_zip = os.path.join(opentrails_dir, 'segments.geojson.zip')
    datastore.download(transformed_segments_zip)

    # Unzip it
    segments_path = unzip(transformed_segments_zip, '.geojson', [])
    transformed_segments = json.load(open(segments_path))
    
    # Generate a list of (name, ids) tuples
    named_trails = make_name_trails(transformed_segments['features'])
    
    named_trails_path = os.path.join(dataset.id, 'opentrails/named_trails.csv')

    with open(named_trails_path, 'w') as named_trails_file:
        cols = 'id', 'name', 'segment_ids', 'description', 'part_of'
        writer = csv.writer(named_trails_file)
        writer.writerow(cols)
        for row in named_trails:
            writer.writerow([row[c] for c in cols])
    
    datastore.upload(named_trails_path)
    
    # Clean up after ourselves.
    shutil.rmtree(dataset.id)

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
        
    opentrails_dir = os.path.join(dataset.id, 'opentrails')
    if not os.path.exists(opentrails_dir):
        os.makedirs(opentrails_dir)
    stewards_path = os.path.join(opentrails_dir, 'stewards.csv')

    with open(stewards_path, 'w') as stewards_file:
        cols = 'id', 'name', 'segment_ids', 'description', 'part_of'
        writer = csv.writer(stewards_file)
        writer.writerow(steward_fields)
        writer.writerow(steward_values)
    
    datastore.upload(stewards_path)
    
    # Clean up after ourselves.
    shutil.rmtree(dataset.id)

    return redirect('/datasets/' + dataset.id + '/stewards', code=303)

@app.route('/datasets/<dataset_id>/stewards')
def view_stewards(dataset_id):
    datastore = make_datastore(app.config['DATASTORE'])
    dataset = get_dataset(datastore, dataset_id)
    if not dataset:
        return make_response("No Dataset Found", 404)
            
    return render_template('dataset-05-stewards.html', dataset=dataset)

@app.route('/datasets/<dataset_id>/upload-trailheads', methods=['POST'])
def upload_trailheads(dataset_id):
    '''
    Upload a zip of one shapefile to datastore
    '''
    datastore = make_datastore(app.config['DATASTORE'])

    # Check that they uploaded a .zip file
    if request.files['file'] and allowed_file(request.files['file'].filename):
        
        # Save zip file to disk
        # /blahblahblah/uploads/trail-trailheads.zip
        upload_dir = os.path.join(dataset_id, 'uploads')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        zipfilepath = os.path.join(upload_dir, 'trail-trailheads.zip')
        request.files['file'].save(zipfilepath)

        # Upload original file to S3
        datastore.upload(zipfilepath)

        # Unzip orginal file
        shapefilepath = unzip(zipfilepath)

        # Get geojson data from shapefile
        geojson = shapefile2geojson(shapefilepath)

        # Write original geojson to file
        geojsonfilepath = zipfilepath.replace('.zip', '.geojson')
        geojsonfile = open(geojsonfilepath,'w')
        geojsonfile.write(json.dumps(geojson, sort_keys=True))
        geojsonfile.close()

        # Compress geojson file
        compress(geojsonfilepath, geojsonfilepath + ".zip")

        # Upload .geojson.zip file to datastore
        datastore.upload(geojsonfilepath + ".zip")
        
        # Clean up after ourselves.
        shutil.rmtree(dataset_id)

        # Show sample data from original file
        return redirect('/datasets/' + dataset_id + "/sample-trailhead")

    else:
        return make_response("Only .zip files allowed", 403)

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
    
    # Clean up after ourselves.
    shutil.rmtree(dataset.id)

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
    upload_dir = os.path.join(dataset.id, 'uploads')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    trailheads_zip = os.path.join(upload_dir, 'trail-trailheads.geojson.zip')
    datastore.download(trailheads_zip)

    # Unzip it
    trailheads_path = unzip(trailheads_zip, '.geojson', [])
    original_trailheads = json.load(open(trailheads_path))
    messages, opentrails_trailheads = trailheads_transform(original_trailheads, dataset)

    # Write files from transformed trailheads
    opentrails_dir = os.path.join(dataset.id, 'opentrails')
    if not os.path.exists(opentrails_dir):
        os.makedirs(opentrails_dir)
    opentrails_trailheads_path = os.path.join(opentrails_dir, 'trailheads.geojson')
    opentrails_trailheads_file = open(opentrails_trailheads_path ,'w')
    opentrails_trailheads_file.write(json.dumps(opentrails_trailheads, sort_keys=True))
    opentrails_trailheads_file.close()
    
    transform_messages_path = dataset.id + "/opentrails/trailheads-messages.json"
    with open(transform_messages_path, 'w') as file:
        json.dump(messages, file)

    # zip up transformed trailheads
    compress(opentrails_trailheads_path, opentrails_trailheads_path + ".zip")

    # Upload transformed trailheads and messages
    datastore.upload(opentrails_trailheads_path + ".zip")
    datastore.upload(transform_messages_path)
    
    # Clean up after ourselves.
    shutil.rmtree(dataset.id)

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
    opentrails_dir = os.path.join(dataset.id, 'opentrails')
    if not os.path.exists(opentrails_dir):
        os.makedirs(opentrails_dir)
    transformed_trailheads_zip = os.path.join(opentrails_dir, 'trailheads.geojson.zip')
    datastore.download(transformed_trailheads_zip)

    # Unzip it
    trailheads_path = unzip(transformed_trailheads_zip, '.geojson', [])
    transformed_trailheads = json.load(open(trailheads_path))
    transformed_features = transformed_trailheads['features'][:3]
    transformed_keys = list(sorted(transformed_features[0]['properties'].keys()))
    
    # Download the transformed trailheads messages file
    transformed_trailheads_messages = dataset.id + '/opentrails/trailheads-messages.json'
    datastore.download(transformed_trailheads_messages)
    
    with open(transformed_trailheads_messages) as f:
        data = json.load(f)
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
    
    # Clean up after ourselves.
    shutil.rmtree(dataset.id)

    return render_template('dataset-08-transformed-trailheads.html', **vars)
        
@app.route('/datasets/<dataset_id>/open-trails.zip')
def download_opentrails_data(dataset_id):
    datastore = make_datastore(app.config['DATASTORE'])
    dataset = get_dataset(datastore, dataset_id)
    if not dataset:
        return make_response("No Dataset Found", 404)

    buffer = package_opentrails_archive(dataset)
    
    return send_file(buffer, 'application/zip')

@app.route('/datasets/<id>')
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
    # steward.get_status()

    # # if steward.status == "transform segments":
    # #     # transform segments
    # #     return redirect("/stewards/"+steward.id+"/transform/segments")
    
    # if steward.status == "show uploaded segments":
    #     sample_segment = get_sample_of_original_segments(steward)

    # if steward.status == "show opentrails segments":
    #     sample_segment = get_sample_of_original_segments(steward)

    #     # Get the segments.geojson.zip
    #     # Download the transformed segments file
    #     segments_zip = steward.id + "/opentrails/segments.geojson.zip"
    #     datastore.download(segments_zip)

    #     # Unzip it
    #     zf = zipfile.ZipFile(segments_zip, 'r')
    #     zf.extractall(os.path.split(segments_zip)[0])

    #     segmentsfile = open(steward.id + "/opentrails/segments.geojson")
    #     trasformed_segments = json.load(segmentsfile)
    #     segmentsfile.close()
    #     opentrails_sample_segment = {'type': 'FeatureCollection', 'features': []}
    #     opentrails_sample_segment['features'].append(trasformed_segments['features'][0])

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
        
    # Save zip file to disk
    # /blahblahblah/uploads/trail-segments.zip
    zipfile_path = os.path.join(dataset_id, 'uploads/open-trails.zip')
    request.files['file'].save(zipfile_path)

    # Upload original file to S3
    datastore.upload(zipfile_path)

    # 
    zf = zipfile.ZipFile(zipfile_path, 'r')
    dirname = os.path.dirname(zipfile_path)
    shapefile_path = None
    
    names = ['trail_segments.geojson', 'named_trails.csv',
             'trailheads.geojson', 'stewards.csv', 'areas.geojson']
    
    for name in sorted(zf.namelist()):
        base, (_, ext) = os.path.basename(name), os.path.splitext(name)
        
        if base in names:
            with open(os.path.join(dataset_id, 'uploads', base), 'w') as file:
                file.write(zf.open(name).read())

    args = [os.path.join(dataset_id, 'uploads', base) for base in names]
    messages, succeeded = check_open_trails(*args)
    
    with open(os.path.join(dataset_id, 'opentrails', 'validate-messages.json'), 'w') as f:
        json.dump(messages, f)
    
    datastore.upload(os.path.join(dataset_id, 'opentrails', 'validate-messages.json'))
    
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

    # Download the transformed segments messages file
    validation_messages = dataset.id + '/opentrails/validate-messages.json'
    datastore.download(validation_messages)
    
    with open(validation_messages) as f:
        messages = map(tuple, json.load(f))
    
    message_types = [message[0] for message in messages]
    
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
