from open_trails import app
from functions import upload_to_s3, download_from_s3, clean_name, make_folders, get_orgs_list
from flask import request, render_template, redirect
import json, os, csv

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/stewards', methods=['POST'])
def stewards():
    '''
    Create a stewards file from the webform
    Upload it to S3
    '''
    org_name, email, phone, url = request.form['name'], request.form['email'], request.form['phone'], request.form['url']
    org_name = clean_name(org_name)
    make_folders(org_name)
    stewards_filepath = os.path.join(org_name, 'uploads', 'stewards.csv')
    with open(stewards_filepath, 'w') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["name","id","url","phone","address","publisher"])
        writer.writerow([org_name,"id",url,phone,"address","publisher"])
    upload_to_s3(stewards_filepath)
    return redirect(org_name)

@app.route('/orgs')
def orgs():
    '''
    List out all the orgs that have used PLATS so far
    '''
    orgs_list = get_orgs_list()
    return render_template('orgs_list.html', orgs_list=orgs_list)

@app.route('/<org_name>')
def existing_org(org_name):
    '''
    Reads available files on S3 to figure out how far an org has gotten in the process
    '''
    make_folders(org_name)
    stewards_filepath = os.path.join(org_name, 'uploads', 'stewards.csv')
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

# @app.route('/map/<org_name>')
# def map_existing_org(org_name):
#     import pdb; pdb.set_trace()
#     filepath = download_s3(org_name)
#     return unzipfile(filepath)
