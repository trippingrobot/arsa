""" Main module """
import json
from werkzeug.routing import Map
from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException, BadRequest
from werkzeug.test import run_wsgi_app
from werkzeug._internal import _log

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
        self.exceptions = []

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
        environ = builder.get_environ()
        resp = run_wsgi_app(app, environ)

        #wrap response
        response = Response(*resp)

        # log response
        print('{host} - - "{method} {path} {protocol}" {status}\n'.format(
            host=environ.get('SERVER_NAME', 'localhost'),
            method=environ.get('REQUEST_METHOD', 'GET'),
            path=environ.get('PATH_INFO', '/'),
            protocol=environ.get('SERVER_PROTOCOL', '/'),
            status=response.status_code
        ))

        return {
            "statusCode": response.status_code,
            "headers": dict(response.headers),
            "body": response.get_data(as_text=True)
        }


    def add_middleware(self, middleware):
        if callable(middleware):
            self.middlewares.append(middleware)

    def add_exception(self, error_type):
        self.exceptions.append(error_type)

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

                if req.form:
                    arguments.update(req.form)

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
                resp = error
            except tuple(self.exceptions) as error:
                code = error.code if hasattr(error, 'code') else 400
                resp = Response(
                    response=json.dumps(error, default=to_serializable),
                    status=code,
                    mimetype='application/json'
                )
            except HTTPException as error:
                resp = Response(
                    response=json.dumps(error, default=to_serializable),
                    status=error.code,
                    mimetype='application/json'
                )

            _request_ctx_stack.pop()

            return resp(environ, start_response)

        return app
