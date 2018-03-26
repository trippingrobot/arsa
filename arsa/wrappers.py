from werkzeug.test import EnvironBuilder

class AWSEnvironBuilder(EnvironBuilder):

    def __init__(self, event, context):
        query_string = None
        if 'queryStringParameters' in event:
            if isinstance(event['queryStringParameters'], dict):
                query_string = '?'.join(
                    ['{}={}'.format(k, v) for k, v in event['queryStringParameters'].items()]
                )

        super(AWSEnvironBuilder, self).__init__(
            path=event['path'],
            method=event['httpMethod'],
            headers=event['headers'],
            data=event['body'],
            query_string=query_string
        )


        self.requestContext = event.get('requestContext', None)


    def get_environ(self):
        environ = super(AWSEnvironBuilder, self).get_environ()
        environ['aws.requestContext'] = self.requestContext
        return environ
