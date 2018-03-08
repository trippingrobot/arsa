from werkzeug.routing import (Rule, RuleFactory)
from werkzeug.exceptions import BadRequest

class Route(Rule):

    def __init__(self, endpoint, **kwargs):
        super(Route, self).__init__('/_arsa', endpoint=endpoint, **kwargs)
        self._conditions = {}
        self._token_required = False

    @property
    def token_required(self):
        return self._token_required

    @token_required.setter
    def token_required(self, value):
        self._token_required = value

    def set_rule(self, rule, methods=None):
        self.rule = rule

        # Taken from super class init method
        if methods is None:
            self.methods = None
        else:
            if isinstance(methods, str):
                raise TypeError('param `methods` should be `Iterable[str]`, not `str`')
            self.methods = set([x.upper() for x in methods])

    def add_validation(self, optional=False, **conditions):
        if optional:
            conditions = {"!{}".format(k): v for k, v in conditions.items()}
        self._conditions.update(conditions)

    def has_valid_arguments(self, arguments):
        if self._conditions is False:
            return True
        for key, condition in self._conditions.items():
            if key.startswith("!"):
                optional_key = key.lstrip('!')
                if optional_key in arguments:
                    if not isinstance(arguments[optional_key], condition):
                        raise BadRequest("argument {} is not of type {}".format(key, condition))
            else:
                if key not in arguments:
                    raise BadRequest(description="argument {} must be supplied".format(key))
                elif not isinstance(arguments[key], condition):
                    raise BadRequest("argument {} is not of type {}".format(key, condition))

        return True


class RouteFactory(RuleFactory):

    def __init__(self):
        self.routes = {}

    def get_rules(self, _):
        for _, route in self.routes.items():
            yield route

    def register_endpoint(self, endpoint):
        if endpoint not in self.routes:
            self.routes[endpoint] = Route(endpoint)

        return self.routes[endpoint]

    def empty(self):
        self.routes = {}
