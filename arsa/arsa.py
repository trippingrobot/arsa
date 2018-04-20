""" Main module """
import json
from werkzeug.routing import Map
from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException, BadRequest
from werkzeug.test import run_wsgi_app
from werkzeug.utils import redirect


from .routes import RouteFactory
from .util import to_serializable
from .wrappers import AWSEnvironBuilder
from .exceptions import Redirect
from .globals import _request_ctx_stack
from .ctx import RequestContext

class Arsa(object):
    """
        Arsa is an object that stores the configuration
        needed for Arsa.io.
    """

    def __init__(self):
        self.factory = RouteFactory()
        self.routes = None
        self.middlewares = []

    def route(self, rule, methods=None, content_type='application/json'):
        """ Convenience decorator for defining a route """
        if methods is None:
            methods = ['GET']

        def decorator(func):
            route = self.factory.register_endpoint(func)
            route.set_rule(rule, methods, mimetype=content_type)
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
            "headers": dict(response.headers),
            "body": response.get_data(as_text=True)
        }


    def add_middleware(self, middleware):
        if callable(middleware):
            self.middlewares.append(middleware)

    def create_app(self):

        if not self.routes:
            self.routes = Map(rules=[self.factory]).bind('arsa.io')

        def app(environ, start_response):
            req = Request(environ)
            _request_ctx_stack.push(RequestContext(req))

            try:

                # Call middlewares
                for middleware in self.middlewares:
                    middleware()

                # Find url rule
                (rule, arguments) = self.routes.match(req.path, method=req.method, return_rule=True)

                arguments.update(dict(req.args))

                if req.data:
                    try:
                        data = json.loads(req.data)
                        arguments.update(data)
                    except ValueError:
                        raise BadRequest("JSON body was malformed")

                rule.has_valid_arguments(arguments)
                decoded_args = rule.decode_arguments(arguments)

                body = rule.endpoint(**decoded_args)

                if rule.mimetype == 'application/json':
                    body = json.dumps(body, default=to_serializable)

                resp = Response(body, mimetype=rule.mimetype)
            except Redirect as error:
                resp = redirect(error.location)
            except HTTPException as error:
                resp = Response(
                    json.dumps(error, default=to_serializable),
                    error.code
                )

            _request_ctx_stack.pop()

            return resp(environ, start_response)

        return app
