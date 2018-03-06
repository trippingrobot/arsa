""" Main module """
import logging
import json
from werkzeug.routing import Map
from werkzeug.wrappers import Request, Response

from .routes import RouteFactory

LOGGER = logging.getLogger(__name__)

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
    def serve(cls, url, method, token=None, **kwargs):
        """ Serve the route by passing the specified keyword
            arguments.
        """
        instance = cls()
        routes = Map(rules=[instance.factory]).bind('arsa.io')
        (rule, arguments) = routes.match(url, method=method, return_rule=True)

        kwargs.update(arguments)
        rule.has_valid_arguments(kwargs)

        if rule.token_required and token is None:
            raise ValueError("Not token sent.")

        LOGGER.log(logging.INFO, "Serving route %s", url)
        return rule.endpoint(**kwargs)

    @classmethod
    def create_app(cls):

        instance = cls()
        routes = Map(rules=[instance.factory]).bind('arsa.io')

        def app(environ, start_response):
            req = Request(environ)

            # Find url rule
            (rule, arguments) = routes.match(req.path, method=req.method, return_rule=True)

            if rule.token_required and 'x-api-token' not in req.headers:
                raise ValueError("Not token sent.")

            if req.data:
                data = json.loads(req.data)
                arguments.update(data)

            rule.has_valid_arguments(arguments)

            LOGGER.log(logging.INFO, "Serving route %s", rule.rule)
            body = rule.endpoint(**arguments)

            response = Response(json.dumps(body), mimetype='application/json')
            return response(environ, start_response)

        return app
