""" Main module """
import json
from werkzeug.routing import Map
from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException, Unauthorized, BadRequest

from .routes import RouteFactory
from .util import to_serializable

class Arsa(object):
    """
        Arsa is a singleton object that stores the configuration
        needed for Arsa.io.
    """

    __instance = None

    def __new__(cls):
        if Arsa.__instance is None:
            Arsa.__instance = object.__new__(cls)
            Arsa.__instance.factory = RouteFactory()
        return Arsa.__instance

    @classmethod
    def route(cls, rule, methods=None):
        """ Convenience decorator for defining a route """
        if methods is None:
            methods = ['GET']

        def decorator(func):
            instance = cls()
            route = instance.factory.register_endpoint(func)
            route.set_rule(rule, methods)
            return func

        return decorator


    @classmethod
    def token_required(cls):
        def decorator(func):
            instance = cls()
            route = instance.factory.register_endpoint(func)
            route.token_required = True
            return func

        return decorator

    @classmethod
    def required(cls, **expected_kwargs):
        def decorator(func):
            instance = cls()
            route = instance.factory.register_endpoint(func)
            route.add_validation(**expected_kwargs)
            return func

        return decorator

    @classmethod
    def optional(cls, **optional_kwargs):
        def decorator(func):
            instance = cls()
            route = instance.factory.register_endpoint(func)
            route.add_validation(True, **optional_kwargs)
            return func

        return decorator

    @classmethod
    def empty(cls):
        instance = cls()
        instance.factory.empty()

    @classmethod
    def create_app(cls, check_token=True):

        instance = cls()
        routes = Map(rules=[instance.factory]).bind('arsa.io')

        def app(environ, start_response):
            try:
                req = Request(environ)

                # Find url rule
                (rule, arguments) = routes.match(req.path, method=req.method, return_rule=True)

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
                resp = error.get_response(environ)
                return resp(environ, start_response)

        return app
