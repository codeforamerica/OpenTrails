from open_trails import app
from werkzeug.utils import secure_filename
import os, boto
from boto.s3.key import Key

app.config['UPLOAD_FOLDER'] = 'uploads'
ALLOWED_EXTENSIONS = set(['zip'])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def dashes(org_name):
    '''
    Replace underscores with dashes in an org_name for prettier urls
    '''
    return org_name.replace("_","-")

def upload_to_s3(org_name, file):
    '''
    Upload a file to S3
    '''
    clean_org_name = dashes(secure_filename(org_name)).lower()
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        conn = boto.connect_s3(app.config["AWS_ACCESS_KEY_ID"], app.config["AWS_SECRET_ACCESS_KEY"])
        mybucket = conn.get_bucket(app.config["S3_BUCKET_NAME"])
        k = Key(mybucket)
        k.key = clean_org_name + '/' + filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        k.set_contents_from_filename(filepath)
        mybucket.set_acl('public-read', k.key)
        conn.close()
        return "https://%s.s3.amazonaws.com/%s/%s" % (app.config["S3_BUCKET_NAME"], clean_org_name, filename)

# def download_s3(org_name):
#     conn = boto.connect_s3(app.config["AWS_ACCESS_KEY_ID"], app.config["AWS_SECRET_ACCESS_KEY"])
#     mybucket = conn.get_bucket(app.config["S3_BUCKET_NAME"])
#     for key in mybucket.list():
#         if org_name in key.name:
#             try:
#                 os.mkdir(os.path.join(app.config['UPLOAD_FOLDER'], org_name))
#             except OSError:
#                 pass
#             key.get_contents_to_filename(os.path.join(app.config['UPLOAD_FOLDER'], key.name))
#     return str(os.path.join(app.config['UPLOAD_FOLDER'], key.name))
