from open_trails import app
from functions import make_datastore, clean_name, unzip, make_id_from_url, compress
from transformers import transform_shapefile, portland_transform, sa_transform
from flask import request, render_template, redirect, make_response
import json, os, csv, zipfile, time

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/new-steward', methods=['POST'])
def new_steward():
    '''
    Create a unique url for this steward to work under
    Create a folder on S3 using this url
    '''
    steward_name, steward_url = request.form['name'], request.form['url']
    steward_id = make_id_from_url(steward_url)
    stewards_filepath = os.path.join(steward_id, 'uploads', 'stewards.csv')
    try:
        os.makedirs(os.path.dirname(stewards_filepath))
    except OSError:
        pass
    with open(stewards_filepath, 'w') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["name","id","url","phone","address","publisher"])
        writer.writerow([steward_name,steward_id,steward_url,"","","yes"])
    datastore = make_datastore(app.config['DATASTORE'])
    datastore.upload(stewards_filepath)
    return redirect('/stewards/' + steward_id)


@app.route('/stewards')
def stewards():
    '''
    List out all the stewards that have used opentrails so far
    '''
    datastore = make_datastore(app.config['DATASTORE'])
    stewards_list = datastore.stewards()
    return render_template('stewards_list.html', stewards_list=stewards_list, server_url=request.url_root)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in set(['zip'])

@app.route('/stewards/<steward_id>/upload', methods=['POST'])
def upload_zip(steward_id):
    '''
    Upload a zip of one shapefile
    '''
    datastore = make_datastore(app.config['DATASTORE'])

    # Check that they uploaded a .zip file
    if request.files['file'] and allowed_file(request.files['file'].filename):
        # Change the uploaded filename to segments.zip, trailheads.zip, etc
        zip_filepath = os.path.join(steward_id, 'uploads', request.form['trailtype'] + '.zip')
        request.files['file'].save(zip_filepath)
        datastore.upload(zip_filepath)
        filename = os.path.split(request.files['file'].filename)[1]
    else:
        return make_response("Only .zip files allowed", 403)

    if request.form['trailtype'] == 'segments':
        return redirect('/stewards/' + steward_id + '/transform/segments')
    if request.form['trailtype'] == 'trailheads':
        return redirect('/stewards/' + steward_id + '/transform/trailheads')

@app.route('/stewards/<steward_id>/transform/<trailtype>')
def transform(steward_id, trailtype):
    '''
    Grab a zip file off of datastore
    Unzip it
    Transform into opentrails
    Upload
    '''
    datastore = make_datastore(app.config['DATASTORE'])
    for filename in datastore.filelist(steward_id):
        # Look for segments.zip or trailheads.zip
        if trailtype + '.zip' in filename:
            datastore.download(filename)
            shapefile_path = unzip(filename)
            raw_geojson = transform_shapefile(shapefile_path)
            opentrails_geojson = {'type': 'FeatureCollection', 'features': []}

            # Transform geojson to opentrails
            if trailtype == 'segments':
                # Only portland so far
                opentrails_geojson = portland_transform(raw_geojson)
                geojson_filename = steward_id + '/opentrails/segments.geojson'
                zip_filename = geojson_filename.replace('.geojson', '.zip')
            
            if trailtype == 'trailheads':
                opentrails_geojson = sa_transform(raw_geojson, steward_id)
                geojson_filename = steward_id + '/opentrails/trailheads.geojson'
                zip_filename = geojson_filename.replace('.geojson', '.zip')

            try:
                os.makedirs(os.path.join(steward_id, 'opentrails'))
            except OSError:
                pass

            output = open(geojson_filename,'w')
            output.write(json.dumps(opentrails_geojson, sort_keys=True))
            output.close()

            # Zip files before uploading them
            compress(geojson_filename, zip_filename)
            datastore.upload(zip_filename)

    return redirect('/stewards/' + steward_id)

@app.route('/stewards/<steward_id>')
def existing_steward(steward_id):
    '''
    Reads available files on S3 to figure out how far a steward has gotten in the process
    '''
    # Init some variables
    stewards_info = False
    geojson = False
    uploaded_stewards = False
    segments_transformed = False
    segments_geojson = False
    trailheads_uploaded = False
    trailheads_geojson = False

    datastore = make_datastore(app.config['DATASTORE'])
    filelist = datastore.filelist(steward_id)
    for file in filelist:
        if 'uploads/stewards.csv' in file:
            uploaded_stewards = True
        if 'opentrails/segments.zip' in file:
            segments_transformed = True
        if 'opentrails/trailheads.zip' in file:
            trailheads_uploaded = True

    if uploaded_stewards:
        stewards_filepath = os.path.join(steward_id, 'uploads', 'stewards.csv')
        datastore.download(stewards_filepath)
        with open(stewards_filepath, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                stewards_info = row

    if segments_transformed:
        datastore.download(steward_id + '/opentrails/segments.zip')
        unzip(steward_id + '/opentrails/segments.zip')
        segments_data = open(steward_id + '/opentrails/segments.geojson')
        segments_geojson = json.load(segments_data)

    if trailheads_uploaded:
        datastore.download(steward_id +'/opentrails/trailheads.zip')
        unzip(steward_id +'/opentrails/trailheads.zip')
        trailhead_data = open(steward_id + '/opentrails/trailheads.geojson')
        trailheads_geojson = json.load(trailhead_data)

    return render_template('index.html', stewards_info = stewards_info, segments_geojson = segments_geojson, trailheads_geojson = trailheads_geojson)

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
