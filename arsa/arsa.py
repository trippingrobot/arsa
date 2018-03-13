""" Main module """
import json
from werkzeug.routing import Map
from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException, Unauthorized, BadRequest
from werkzeug.test import EnvironBuilder, run_wsgi_app
from werkzeug.utils import escape

from .routes import RouteFactory
from .util import to_serializable

class Arsa(object):
    """
        Arsa is an object that stores the configuration
        needed for Arsa.io.
    """

    def __init__(self):
        self.factory = RouteFactory()
        self.routes = None

    def route(self, rule, methods=None):
        """ Convenience decorator for defining a route """
        if methods is None:
            methods = ['GET']

        def decorator(func):
            route = self.factory.register_endpoint(func)
            route.set_rule(rule, methods)
            return func

        return decorator


    def token_required(self):
        def decorator(func):
            route = self.factory.register_endpoint(func)
            route.token_required = True
            return func

        return decorator

    def required(self, **expected_kwargs):
        def decorator(func):
            route = self.factory.register_endpoint(func)
            route.add_validation(**expected_kwargs)
            return func

        return decorator

    def optional(self, **optional_kwargs):
        def decorator(func):
            route = self.factory.register_endpoint(func)
            route.add_validation(True, **optional_kwargs)
            return func

        return decorator

    def handler(self, event, context):
        app = self.create_app(check_token=False)

        if 'queryStringParameters' in event:
            query_string = '?'.join(['{}={}'.format(k, v) for k, v in event['queryStringParameters'].items()])
        else:
            query_string = None

        builder = EnvironBuilder(
            path=event['path'],
            method=event['httpMethod'],
            headers=event['headers'],
            data=event['body'],
            query_string=query_string
        )
        builder.close()
        resp = run_wsgi_app(app, builder.get_environ())

        #wrap response
        response = Response(*resp)

        return {
            "statusCode": response.status_code,
            "body": response.get_data(as_text=True)
        }

    def create_app(self, check_token=True):

        if not self.routes:
            self.routes = Map(rules=[self.factory]).bind('arsa.io')

        def app(environ, start_response):
            try:
                req = Request(environ)

                # Find url rule
                (rule, arguments) = self.routes.match(req.path, method=req.method, return_rule=True)

                if check_token and rule.token_required and 'x-api-token' not in req.headers:
                    raise Unauthorized("Not token sent.")


                if req.data:
                    try:
                        data = json.loads(req.data)
                        arguments.update(data)
                    except ValueError:
                        raise BadRequest("JSON body was malformed")

                rule.has_valid_arguments(arguments)
                decoded_args = rule.decode_arguments(arguments)

                body = rule.endpoint(**decoded_args)

                response = Response(json.dumps(body, default=to_serializable), mimetype='application/json')
                return response(environ, start_response)
            except HTTPException as error:
                body = json.dumps({
                    "error": error.name,
                    "description": error.description
                })
                resp = Response(body, error.code, error.get_headers(environ))
                return resp(environ, start_response)

        return app
