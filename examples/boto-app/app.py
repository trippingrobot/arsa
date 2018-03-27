import boto3

from arsa import Arsa
app = Arsa()

@app.route("/buckets")
def list_buckets():
    """ List buckets """
    client = boto3.client('s3')
    buckets = client.list_buckets()

    return buckets
