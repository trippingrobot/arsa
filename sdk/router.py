""" Router """

import logging
from .exceptions import BadRoute

LOGGER = logging.getLogger(__name__)

class Router(object):
    """ Router class to map and serve requests from AWS Lambda
        to a defined function.

        Use the @Router.route(path) decorator to define a new route.

        Call the function router.serve(path) to call the appropriate function.
    """
    __instance = None

    def __new__(cls):
        if Router.__instance is None:
            Router.__instance = object.__new__(cls)
            Router.__instance.routes = {}
        return Router.__instance

    @classmethod
    def route(cls, route_str):
        """ Create a route mapping from the route_str """

        def decorator(func):
            """ decorator function"""
            instance = cls()
            instance.routes[route_str] = func
            return func

        return decorator

    def serve(self, route, **kwargs):
        """ Serve the route by passing the specified keyword
            arguments.
        """
        if self.routes.get(route) is None:
            raise BadRoute("Invalid route %s" % route)

        LOGGER.log(logging.INFO, "Serving route %s", route)
        return self.routes.get(route)(**kwargs)
