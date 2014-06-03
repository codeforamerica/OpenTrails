[![Build Status](https://travis-ci.org/codeforamerica/PLATS.png)](https://travis-ci.org/codeforamerica/PLATS)

OpenTrails Converter
=====

Description
-----------

This in-development tool will allow park agencies and other trail data stewards to upload and transformer their existing shapefile data describing trail networks—including trail segments, trailheads, and the areas they traverse—into OpenTrails-compliant GeoJSON and CSV files.


Install
-------

PLATS is a [Python Flask application](https://github.com/codeforamerica/howto/blob/master/Python-Virtualenv.md),
and depends on [Amazon S3](http://aws.amazon.com/s3/) for storage of uploads.
Amazon Web Services configuration comes from the `DATASTORE` environmental
variable, given in this form:

    s3n://<AWS key>:<AWS secret>@<S3 bucket name>

PLATS doesn’t do a lot at the moment.
