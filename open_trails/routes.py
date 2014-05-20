from open_trails import app
from functions import upload_to_s3, download_from_s3, clean_name, make_folders, get_stewards_list
from flask import request, render_template, redirect
import json, os, csv

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
    make_folders(steward_name)
    stewards_filepath = os.path.join(steward_name, 'uploads', 'stewards.csv')
    with open(stewards_filepath, 'w') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["name","id","url","phone","address","publisher"])
        writer.writerow([steward_name,"id",url,phone,"address","publisher"])
    upload_to_s3(stewards_filepath)
    return redirect(steward_name)

@app.route('/stewards')
def stewards():
    '''
    List out all the stewards that have used PLATS so far
    '''
    stewards_list = get_stewards_list()
    return render_template('stewards_list.html', stewards_list=stewards_list)

@app.route('/stewards/<steward_name>')
def existing_steward(steward_name):
    '''
    Reads available files on S3 to figure out how far an org has gotten in the process
    '''
    import pdb; pdb.set_trace()
    make_folders(steward_name)
    stewards_filepath = os.path.join(steward_name, 'uploads', 'stewards.csv')
    download_from_s3(stewards_filepath)
    with open(stewards_filepath, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            stewards_info = row
    return render_template('index.html', stewards_info=stewards_info)

# @app.route('/upload', methods=['POST'])
# def upload():
#     return upload_to_s3(request.form['org-name'], request.files['file'])
    # return s3_file_url

# @app.route('/map', methods=['POST'])
# def map():
#     data = transformers.transform_shapefile(shapefile)
#     return render_template('map.html', data = data)

# @app.route('/map/<steward_name>')
# def map_existing_org(steward_name):
#     import pdb; pdb.set_trace()
#     filepath = download_s3(steward_name)
#     return unzipfile(filepath)
