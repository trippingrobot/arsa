from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

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

        self.context = context
