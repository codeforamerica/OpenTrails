from open_trails import app
from functions import make_datastore, clean_name, unzip
from transformers import transform_shapefile
from flask import request, render_template, redirect
import json, os, csv, zipfile

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/new-steward', methods=['POST'])
def new_steward():
    '''
    Create a stewards file from the webform
    Upload it to S3
    '''
    steward_name, email, phone, url = request.form['name'], request.form['email'], request.form['phone'], request.form['url']
    steward_name = clean_name(steward_name)
    stewards_filepath = os.path.join(steward_name, 'uploads', 'stewards.csv')
    try:
        os.makedirs(os.path.dirname(stewards_filepath))
    except OSError:
        pass
    with open(stewards_filepath, 'w') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["name","id","url","phone","address","publisher"])
        writer.writerow([steward_name,"id",url,phone,"address","publisher"])
    datastore = make_datastore(app.config['DATASTORE'])
    datastore.upload(stewards_filepath)
    return redirect('/stewards/' + steward_name)


@app.route('/stewards')
def stewards():
    '''
    List out all the stewards that have used PLATS so far
    '''
    datastore = make_datastore(app.config['DATASTORE'])
    stewards_list = datastore.stewards()
    return render_template('stewards_list.html', stewards_list=stewards_list, server_url=request.url_root)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in set(['zip'])

@app.route('/stewards/<steward_name>/upload-zip', methods=['POST'])
def upload_zip(steward_name):
    '''
    Upload a zip full of shapefiles
    '''
    zip_filepath = os.path.join(steward_name, 'uploads', request.files['file'].filename)
    if request.files['file'] and allowed_file(request.files['file'].filename):
        request.files['file'].save(zip_filepath)
        upload_to_s3(zip_filepath)
    return redirect('/stewards/' + steward_name)


@app.route('/stewards/<steward_name>')
def existing_steward(steward_name):
    '''
    Reads available files on S3 to figure out how far a steward has gotten in the process
    '''
    # Init some variables
    stewards_info = False
    geojson = False
    uploaded_stewards = False
    uploaded_zip = False
    datastore = make_datastore(app.config['DATASTORE'])
    filelist = datastore.filelist(steward_name)
    for file in filelist:
        if 'stewards.csv' in file:
            uploaded_stewards = True
        if '.zip' in file:
            uploaded_zip = True

    if uploaded_stewards:
        stewards_filepath = os.path.join(steward_name, 'uploads', 'stewards.csv')
        datastore.download(stewards_filepath)
        with open(stewards_filepath, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                stewards_info = row

    if uploaded_zip:
        for file in filelist:
            if '.zip' in file:
                download_from_s3(file)
                filepath = file
                break
        shapefile_path = unzip(filepath)
        geojson = transform_shapefile(shapefile_path)

    return render_template('index.html', stewards_info = stewards_info, geojson = geojson)
