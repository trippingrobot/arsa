""" Main module """
import json
from werkzeug.routing import Map
from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException, BadRequest
from werkzeug.test import run_wsgi_app

from .routes import RouteFactory
from .util import to_serializable
from .policy import Policy
from .wrappers import AWSEnvironBuilder

class Arsa(object):
    """
        Arsa is an object that stores the configuration
        needed for Arsa.io.
    """

    def __init__(self):
        self.factory = RouteFactory()
        self.routes = None

        self.authorizer_func = None

    def route(self, rule, methods=None, content_type='application/json', inject_request=False):
        """ Convenience decorator for defining a route """
        if methods is None:
            methods = ['GET']

        def decorator(func):
            route = self.factory.register_endpoint(func)
            route.set_rule(rule, methods, mimetype=content_type, inject_request=inject_request)
            return func

        return decorator


    def authorizer(self):
        """ Set the authorizer function """
        def decorator(func):
            self.authorizer_func = func
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
        app = self.create_app()

        builder = AWSEnvironBuilder(event, context)
        builder.close()
        resp = run_wsgi_app(app, builder.get_environ())

        #wrap response
        response = Response(*resp)

        return {
            "statusCode": response.status_code,
            "body": response.get_data(as_text=True)
        }

    def authorize(self, auth_event, context):
        policy = Policy(auth_event)

        if self.authorizer_func:
            policy = self.authorizer_func(auth_event, context)

        return policy.as_dict()

    def create_app(self):

        if not self.routes:
            self.routes = Map(rules=[self.factory]).bind('arsa.io')

        def app(environ, start_response):
            try:
                req = Request(environ)

                # Find url rule
                (rule, arguments) = self.routes.match(req.path, method=req.method, return_rule=True)

                if req.data:
                    try:
                        data = json.loads(req.data)
                        arguments.update(data)
                    except ValueError:
                        raise BadRequest("JSON body was malformed")

                rule.has_valid_arguments(arguments)
                decoded_args = rule.decode_arguments(arguments)

                if rule.inject_request:
                    decoded_args['arsa_request'] = req

                body = rule.endpoint(**decoded_args)

                response = Response(
                    json.dumps(body, default=to_serializable), mimetype=rule.mimetype
                )
                return response(environ, start_response)
            except HTTPException as error:
                resp = Response(
                    json.dumps(error, default=to_serializable),
                    error.code,
                    error.get_headers(environ)
                )
                return resp(environ, start_response)

        return app
