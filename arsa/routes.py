from collections import namedtuple
from werkzeug.routing import (Rule, RuleFactory)
from werkzeug.exceptions import BadRequest


from .model import valid_arguments, Attribute, Model, ListType, ListAttribute
from .exceptions import ArgumentKeyError

class Route(Rule):

    def __init__(self, endpoint, **kwargs):
        super(Route, self).__init__('/_arsa', endpoint=endpoint, **kwargs)
        self._conditions = {}
        self.mimetype = None

    def set_rule(self, rule, methods=None, mimetype=None):
        self.rule = rule
        self.mimetype = mimetype
        # Taken from super class init method
        if methods is None:
            self.methods = None
        else:
            if isinstance(methods, str):
                raise TypeError('param `methods` should be `Iterable[str]`, not `str`')
            self.methods = set([x.upper() for x in methods])

    def add_validation(self, optional=False, **conditions):
        if 'query' in conditions:
            raise ValueError('The query named parameter is reserved.')

        conditions = {k: ListAttribute(typeof=v._type, optional=optional)
                         if issubclass(v, ListType) else Attribute(v, optional=optional)
                      for k, v in conditions.items()}
        self._conditions.update(conditions)

    def has_valid_arguments(self, arguments):
        try:
            valid_arguments(self.endpoint.__name__, arguments, self._conditions)
        except ArgumentKeyError as key_error:
            raise BadRequest(str(key_error))

        return True

    def decode_arguments(self, arguments):
        for key, value in arguments.items():
            if key in self._conditions:
                attr = self._conditions[key]
                if issubclass(attr.attr_type, Model):
                    arguments[key] = attr.attr_type(**value)
                elif isinstance(attr, ListAttribute) is False and isinstance(value, list) and len(value) == 1:
                    arguments[key] = value[0]

        return arguments

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
