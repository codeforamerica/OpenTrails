from open_trails import app
from models import Steward, make_datastore
from functions import get_steward, clean_name, unzip, make_id_from_url, compress, allowed_file
from transformers import shapefile2geojson, portland_transform, sa_transform
from flask import request, render_template, redirect, make_response
import json, os, csv, zipfile, time, re

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/new-steward', methods=['POST'])
def new_steward():
    '''
    Create a unique url for this steward to work under
    Create a folder on S3 using this url
    '''

    # Get info from form
    name, url = request.form['name'], request.form['url']
    id = make_id_from_url(url)

    # Make a new steward object
    steward_info = {"id":id, "name":name, "url":url, "phone":None, "address":None, "publisher":"yes"}
    steward = Steward(steward_info)
    steward.datastore = make_datastore(app.config['DATASTORE'])
    
    # Make local folders for steward
    try:
        os.makedirs(steward.id + "/uploads")
        os.makedirs(steward.id + "/opentrails")
    except OSError:
        pass

    # Write a stewards.csv file
    stewards_info_filepath = os.path.join(steward.id, 'uploads', 'stewards.csv')
    with open(stewards_info_filepath, 'w') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["name","id","url","phone","address","publisher"])
        writer.writerow([steward.name,steward.id,steward.url,steward.phone,steward.address,steward.publisher])
    
    # Upload stewards.csv to datastore
    steward.datastore.upload(stewards_info_filepath)
    return redirect('/stewards/' + steward.id)


@app.route('/stewards/<steward_id>/upload', methods=['POST'])
def upload(steward_id):
    '''
    Upload a zip of one shapefile to datastore
    '''
    datastore = make_datastore(app.config['DATASTORE'])

    # Check that they uploaded a .zip file
    if request.files['file'] and allowed_file(request.files['file'].filename):
        
        # Save zip file to disk
        # /examplesteward/uploads/mytrailsegments.zip
        zipfilepath = os.path.join(steward_id, 'uploads', request.files['file'].filename)
        request.files['file'].save(zipfilepath)

        # Upload original file to S3
        datastore.upload(zipfilepath)

        # Unzip orginal file
        zf = zipfile.ZipFile(zipfilepath, 'r')
        zf.extractall(os.path.split(zipfilepath)[0])

        # Find shapefile in zip
        for file in os.listdir(os.path.split(zipfilepath)[0]):
            if '.shp' in file:
                shapefilepath = os.path.join(os.path.split(zipfilepath)[0], file)

        # Get geojson data from shapefile
        geojson = shapefile2geojson(shapefilepath)

        # clean up - delete uneeded shapefiles
        dont_delete = ['csv','zip','geojson']
        for file in os.listdir(steward_id + '/uploads'):
            if file.split('.')[1] not in dont_delete: 
                os.remove(steward_id + '/uploads/' + file)

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
        return redirect('/stewards/' + steward_id)

    else:
        return make_response("Only .zip files allowed", 403)


@app.route('/stewards/<id>/transform/<trailtype>')
def transform(id, trailtype):
    '''
    Grab a zip file off of datastore
    Unzip it
    Transform into opentrails
    Upload
    '''
    datastore = make_datastore(app.config['DATASTORE'])
    steward = get_steward(datastore, id)
    if not steward:
        return make_response("No Steward Found", 404)

    if trailtype == "segments":
        # Download the original segments file
        filelist = datastore.filelist(steward.id)
        matching = [filename for filename in filelist if ".geojson.zip" in filename]
        segments_zip = matching[0]
        datastore.download(segments_zip)

        # Unzip it
        zf = zipfile.ZipFile(segments_zip, 'r')
        zf.extractall(os.path.split(segments_zip)[0])

        # Find geojson file
        for file in os.listdir(steward.id + "/uploads/"):
            if file.endswith(".geojson"):
                segmentsfile = open(steward.id + "/uploads/" + file)
                original_segments = json.load(segmentsfile)
                segmentsfile.close()
                import pdb; pdb.set_trace()
                opentrails_segments = segments_transform(original_segments, steward)

        # Write file from transformed segments
        opentrails_segments_path = steward.id + "/opentrails/segments.geojson"
        opentrails_segments_file = open(opentrails_segments_path ,'w')
        opentrails_segments_file.write(json.dumps(opentrails_segments, sort_keys=True))
        opentrails_segments_file.close()

        # zip up transformed segments
        compress(opentrails_segments_path, opentrails_segments_path + ".zip")

        # Upload transformed segments
        datastore.upload(opentrails_segments_path + ".zip")

        return redirect('/stewards/' + steward.id)

@app.route('/stewards/<id>')
def existing_steward(id):
    '''
    Reads available files on S3 to figure out how far a steward has gotten in the process
    '''

    datastore = make_datastore(app.config['DATASTORE'])
    steward = get_steward(datastore, id)
    if not steward:
        return make_response("No Steward Found", 404)
    steward.get_status()

    if steward.status == "has segments":
        # transform segments
        return redirect("/stewards/"+steward.id+"/transform/segments")
    
    if steward.status == "show segments":
        # unzip segments
        zf = zipfile.ZipFile(steward.id + "/opentrails/segments.geojson.zip", 'r')
        zf.extractall(steward.id + "/opentrails")

        # show segments on a map
        opentrails_segments_file = open(steward.id + "/opentrails/segments.geojson","r")
        opentrails_segments = json.load(opentrails_segments_file)
        opentrails_segments_file.close() 
    else:
        opentrails_segments = False

    return render_template('index.html', steward = steward, opentrails_segments = opentrails_segments)


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
