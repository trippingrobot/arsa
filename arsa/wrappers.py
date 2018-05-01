import re
from werkzeug.test import EnvironBuilder

class AWSEnvironBuilder(EnvironBuilder):

    def __init__(self, event, context):
        query_string = None
        if 'queryStringParameters' in event:
            if isinstance(event['queryStringParameters'], dict):
                query_string = '?'.join(
                    ['{}={}'.format(k, v) for k, v in event['queryStringParameters'].items()]
                )

        if 'stage' in event['requestContext']:
            stage = event['requestContext']['stage']
            path = re.sub(r'^/%s/' % stage, '/', event['path'])
        else:
            path = event['path']

        print(path)
        super(AWSEnvironBuilder, self).__init__(
            path=path,
            method=event['httpMethod'],
            headers=event['headers'],
            data=event['body'],
            query_string=query_string
        )


        self.request_context = event.get('requestContext', None)
        self.lambda_context = context

    def get_environ(self):
        environ = super(AWSEnvironBuilder, self).get_environ()
        environ['aws.requestContext'] = self.request_context
        environ['aws.lambdaContext'] = self.lambda_context
        return environ
