[![Build Status](https://travis-ci.org/codeforamerica/PLATS.png)](https://travis-ci.org/codeforamerica/PLATS)

PLATS
=====

Public Land and Trail Specification

Install
-------

PLATS is a [Python Flask application](https://github.com/codeforamerica/howto/blob/master/Python-Virtualenv.md),
and depends on [Amazon S3](http://aws.amazon.com/s3/) for storage of uploads.
Amazon Web Services configuration comes from the `DATASTORE` environmental
variable, given in this form:

    s3n://<AWS key>:<AWS secret>/<S3 bucket name>

PLATS doesn’t do a lot at the moment.
