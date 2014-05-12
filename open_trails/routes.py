from open_trails import app, transformers
from flask import request, render_template

@app.route('/', methods=['GET', 'POST'])
def index():
    # Show an uplaod form or process an uploaded shapefile
    if request.method == 'POST':
        return transformers.transform_shapefile(request.files['file'])

    if request.method == 'GET':
        return render_template('index.html')
