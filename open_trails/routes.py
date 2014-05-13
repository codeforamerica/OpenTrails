from open_trails import app, transformers
from flask import request, render_template
import json

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/map', methods=['POST'])
def map():
    # import pdb; pdb.set_trace()
    # Show an uplaod form or process an uploaded shapefile
    data = transformers.transform_shapefile(request.files['file'])
    return render_template('map.html', data = data)
