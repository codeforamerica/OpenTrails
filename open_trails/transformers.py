import os, json, subprocess

def shp2geojson(filename):
    '''Converts a shapefile to a geojson file with spherical mercator.
    '''
    in_file = filename
    out_file = '{0}.geojson'.format(filename)

    args = 'ogr2ogr -t_srs EPSG:4326 -f GeoJSON ___ ___'.split()
    args[-2:] = out_file, in_file
    if os.path.exists(out_file):
        os.remove(out_file)
    subprocess.check_call(args)
    return out_file

def open_geojson(geojson_path):
    '''Reads a geojson file. Returns a python obj.
    '''
    json_data=open(geojson_path)
    data = json.load(json_data)
    json_data.close()
    return data

def transform_shapefile(shapefile_path):
    '''
    Convert a shp file to a geojson file
    Open geojson file and return it as a python obj.
    '''
    geojson_path = shp2geojson(shapefile_path)
    data = open_geojson(geojson_path)
    return data
