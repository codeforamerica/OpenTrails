from open_trails import app
from models import Dataset, make_datastore
from functions import (
    get_dataset, clean_name, unzip, make_id_from_url, compress, allowed_file,
    get_sample_of_original_segments, make_name_trails
    )
from transformers import shapefile2geojson, segments_transform
from flask import request, render_template, redirect, make_response
import json, os, csv, zipfile, time, re

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
        zipfilepath = os.path.join(dataset_id, 'uploads/trail-segments.zip')
        request.files['file'].save(zipfilepath)

        # Upload original file to S3
        datastore.upload(zipfilepath)

        # Unzip orginal file
        shapefilepath = unzip(zipfilepath)

        # Get geojson data from shapefile
        geojson = shapefile2geojson(shapefilepath)

        # clean up - delete uneeded shapefiles
        dont_delete = ['.csv','.zip','.geojson']
        for file in os.listdir(dataset_id + '/uploads'):
            if os.path.splitext(file)[1] not in dont_delete: 
                os.remove(dataset_id + '/uploads/' + file)

        # Write original geojson to file
        geojsonfilepath = zipfilepath.replace('.zip', '.geojson')
        geojsonfile = open(geojsonfilepath,'w')
        geojsonfile.write(json.dumps(geojson, sort_keys=True))
        geojsonfile.close()

        # Compress geojson file
        compress(geojsonfilepath, geojsonfilepath + ".zip")

        # Upload .geojson.zip file to datastore
        datastore.upload(geojsonfilepath + ".zip")

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

    sample_segment = get_sample_of_original_segments(dataset)
    return render_template("dataset-02-show-sample-segment.html", dataset=dataset, sample_segment=sample_segment)

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
    segments_zip = dataset.id + '/uploads/trail-segments.geojson.zip'
    datastore.download(segments_zip)

    # Unzip it
    segments_path = unzip(segments_zip, '.geojson', [])
    original_segments = json.load(open(segments_path))
    messages, opentrails_segments = segments_transform(original_segments, dataset)

    # Write files from transformed segments
    opentrails_segments_path = dataset.id + "/opentrails/segments.geojson"
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

    return redirect('/datasets/' + dataset.id + '/transformed-segments', code=303)
        
@app.route('/datasets/<dataset_id>/transformed-segments')
def transformed_segments(dataset_id):
    datastore = make_datastore(app.config['DATASTORE'])
    dataset = get_dataset(datastore, dataset_id)
    if not dataset:
        return make_response("No Dataset Found", 404)

    # Download the original segments file
    original_segments_zip = dataset.id + '/uploads/trail-segments.geojson.zip'
    datastore.download(original_segments_zip)

    # Unzip it
    segments_path = unzip(original_segments_zip, '.geojson', [])
    original_segments = json.load(open(segments_path))
    sample_segment = {'type': 'FeatureCollection', 'features': []}
    sample_segment['features'].append(original_segments['features'][0])
    
    # Download the transformed segments file
    transformed_segments_zip = dataset.id + '/opentrails/segments.geojson.zip'
    datastore.download(transformed_segments_zip)

    # Unzip it
    segments_path = unzip(transformed_segments_zip, '.geojson', [])
    transformed_segments = json.load(open(segments_path))
    opentrails_sample_segment = {'type': 'FeatureCollection', 'features': []}
    opentrails_sample_segment['features'].append(transformed_segments['features'][0])
    
    # Download the transformed segments messages file
    transformed_segments_messages = dataset.id + '/opentrails/segments-messages.json'
    datastore.download(transformed_segments_messages)
    
    with open(transformed_segments_messages) as f:
        messages = json.load(f)
    
    message_types = [type for (type, message) in messages]
    
    vars = dict(
        dataset = dataset,
        messages = messages,
        sample_segment = sample_segment,
        opentrails_sample_segment = opentrails_sample_segment,
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
    transformed_segments_zip = dataset.id + '/opentrails/segments.geojson.zip'
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
    
    from flask import jsonify
    return jsonify(dict(n=list(named_trails)))
            
    return render_template('dataset-03-transformed-segments.html', dataset=dataset, messages=messages, sample_segment = sample_segment, opentrails_sample_segment = opentrails_sample_segment)
    


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
