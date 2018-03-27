import os
from unittest.mock import patch
import boto3
import placebo
from werkzeug.serving import WSGIRequestHandler

MOCKS = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'mocks')

def fake_boto3_client(*args, **kwargs):
    session = boto3.Session()
    pill = placebo.attach(session, data_path=MOCKS)
    pill.playback()
    return session.client(*args, **kwargs)

class MockAWSHandler(WSGIRequestHandler):

    def run_wsgi(self):
        with patch('boto3.client', fake_boto3_client):
            super(MockAWSHandler, self).run_wsgi()

    def make_environ(self):
        environ = super(MockAWSHandler, self).make_environ()
        environ['aws.requestContext'] = {
            'authorizer': {
                'principalId': '1234'
            }
        }
        return environ
