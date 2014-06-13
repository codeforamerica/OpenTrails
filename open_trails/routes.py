from open_trails import app
from models import Steward, make_datastore
from functions import make_steward_from_datastore, clean_name, unzip, make_id_from_url, compress, allowed_file
from transformers import shapefile2geojson, portland_transform, sa_transform
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
    # Get info from form
    name, url = request.form['name'], request.form['url']
    id = make_id_from_url(url)

    # Make a new steward object
    steward = Steward(id=id, name=name, url=url, phone=None, address=None, publisher="yes")
    
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
    datastore = make_datastore(app.config['DATASTORE'])
    datastore.upload(stewards_info_filepath)
    return redirect('/stewards/' + steward.id)


@app.route('/stewards')
def stewards():
    '''
    List out all the stewards that have used opentrails so far
    '''
    datastore = make_datastore(app.config['DATASTORE'])
    stewards_list = datastore.stewards()
    return render_template('stewards_list.html', stewards_list=stewards_list, server_url=request.url_root)


@app.route('/stewards/<steward_id>/upload', methods=['POST'])
def upload_zip(steward_id):
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

        # Upload .geojson file to datastore
        datastore.upload(geojsonfilepath)

        # Show sample data from original file
        return redirect('/stewards/' + steward_id)

    else:
        return make_response("Only .zip files allowed", 403)

# @app.route("/stewards/<steward_id>/transform/<trailtype>/shp2geojson")
# def shp2geojson(steward_id, trailtype):
#     '''
#         Convert shapefile to geojson
#     '''
#     datastore = make_datastore(app.config['DATASTORE'])
#     for filename in datastore.filelist(steward_id):
        
#         # Look for segments.zip or trailheads.zip
#         if trailtype + '.zip' in filename:

#             # Check that it hasn't been shp2geojson'd yet
#             if filename.replace('.zip', '.geojson.zip') not in datastore.filelist(steward_id):
                
#                 datastore.download(filename)
#                 shapefile_path = unzip(filename)
                
#                 # Transform the og shapefile
#                 raw_geojson = transform_shapefile(shapefile_path)

#                 # clean up - delete shapefiles
#                 dont_delete = ['stewards.csv','segments.zip','namedtrails.csv','trailheads.zip','areas.zip']
#                 for file in os.listdir(os.path.split(filename)[0]):
#                     if file not in dont_delete: 
#                         os.remove(os.path.split(filename)[0]+'/'+file)

#                 # Write the raw geojson to a file
#                 output = open(filename.replace('.zip', '.geojson'),'w')
#                 output.write(json.dumps(raw_geojson, sort_keys=True))
#                 output.close()

#                 # Compress big geojson
#                 compress(filename.replace('.zip', '.geojson'), filename.replace('.zip', '.geojson.zip'))

#                 # Upload raw geojson to /uploads
#                 datastore.upload(filename.replace('.zip', '.geojson.zip'))

#                 return redirect('/stewards/' + steward_id)

# @app.route('/stewards/<steward_id>/transform/<trailtype>')
# def transform(steward_id, trailtype):
#     '''
#     Grab a zip file off of datastore
#     Unzip it
#     Transform into opentrails
#     Upload
#     '''
#     datastore = make_datastore(app.config['DATASTORE'])
#     for filename in datastore.filelist(steward_id):
        
#         # Look for segments.zip or trailheads.zip
#         if trailtype + '.zip' in filename:
#             datastore.download(filename)
#             shapefile_path = unzip(filename)
            
#             # Transform the og shapefile
#             raw_geojson = transform_shapefile(shapefile_path)
            
#             # delete shapefiles
#             dont_delete = ['stewards.csv','segments.zip','namedtrails.csv','trailheads.zip','areas.zip']
#             for file in os.listdir(os.path.split(filename)[0]):
#                 if file not in dont_delete: 
#                     os.remove(os.path.split(filename)[0]+'/'+file)

#             # Transform geojson to opentrails
#             if trailtype == 'segments':
#                 # Only portland so far
#                 opentrails_geojson = portland_transform(raw_geojson)
#                 geojson_filename = steward_id + '/opentrails/segments.geojson'
#                 zip_filename = geojson_filename.replace('.geojson', '.zip')
            
#             if trailtype == 'trailheads':
#                 opentrails_geojson = sa_transform(raw_geojson, steward_id)
#                 geojson_filename = steward_id + '/opentrails/trailheads.geojson'
#                 zip_filename = geojson_filename.replace('.geojson', '.zip')

#             try:
#                 os.makedirs(os.path.join(steward_id, 'opentrails'))
#             except OSError:
#                 pass

#             output = open(geojson_filename,'w')
#             output.write(json.dumps(opentrails_geojson, sort_keys=True))
#             output.close()

#             # Zip files before uploading them
#             compress(geojson_filename, zip_filename)
#             datastore.upload(zip_filename)

#     return redirect('/stewards/' + steward_id)

@app.route('/stewards/<id>')
def existing_steward(id):
    '''
    Reads available files on S3 to figure out how far a steward has gotten in the process
    '''

    # Init some variables
    # stewards_info = False
    # geojson = False
    # uploaded_stewards = False
    # uploaded_segments = False
    # segments_transformed = False
    # segments_geojson = False
    # trailheads_uploaded = False
    # trailheads_geojson = False
    # sample_geojson = False
    # raw_segments = False
    # sample_segment = False

    datastore = make_datastore(app.config['DATASTORE'])
    filelist = datastore.filelist(id)

    for filepath in filelist:
        if 'uploads/stewards.csv' in filepath:
            steward = make_steward_from_datastore(datastore, filepath)
    #     if 'uploads/segments.zip' in file:
    #         uploaded_segments = True
    #     if 'uploads/segments.geojson.zip' in file:
    #         raw_segments = True
        # if 'opentrails/segments.zip' in file:
        #     segments_transformed = True
        # if 'opentrails/trailheads.zip' in file:
        #     trailheads_uploaded = True

    # if raw_segments:
    #     # Show a sample of what was uploaded
    #     filepath = steward_id + '/uploads/segments.geojson.zip'
    #     datastore.download(filepath)
    #     zf = zipfile.ZipFile(filepath, 'r')
    #     zf.extractall(os.path.split(filepath)[0])
    #     raw_segments_data = open(steward_id + '/uploads/segments.geojson')
    #     raw_segments_geojson = json.load(raw_segments_data)
    #     sample_segment = {'type': 'FeatureCollection', 'features': []}
    #     sample_segment['features'].append(raw_segments_geojson['features'][0])

    # if segments_transformed:
    #     datastore.download(steward_id + '/opentrails/segments.zip')
    #     unzip(steward_id + '/opentrails/segments.zip')
    #     segments_data = open(steward_id + '/opentrails/segments.geojson')
    #     segments_geojson = json.load(segments_data)
    #     sample_segment = {'type': 'FeatureCollection', 'features': [segments_geojson['features'][0]]}

    # if trailheads_uploaded:
    #     datastore.download(steward_id +'/opentrails/trailheads.zip')
    #     unzip(steward_id +'/opentrails/trailheads.zip')
    #     trailhead_data = open(steward_id + '/opentrails/trailheads.geojson')
    #     trailheads_geojson = json.load(trailhead_data)

    return render_template('index.html', steward = steward)
    # return render_template('index.html', stewards_info = stewards_info, segments_geojson = sample_geojson, trailheads_geojson = trailheads_geojson)

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
