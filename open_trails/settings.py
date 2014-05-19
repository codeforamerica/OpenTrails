from open_trails import app
import os

app.config.update(
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID'),
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY'),
    S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
)
