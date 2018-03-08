""" model.py """
from inspect import getmembers
from .exceptions import ArgumentKeyError

class Attribute(object):

    def __init__(self, attr_type, optional=False):
        self.attr_type = attr_type
        self.optional = optional

class Model(object):
    """ Abstract class to wrap custom object attributes """

    @classmethod
    def _get_properties(cls):
        """ Return a dict of the models attributes """
        properties = {}
        for name, attribute in getmembers(cls, lambda attr: isinstance(attr, Attribute)):
            properties[name] = attribute

        return properties

def valid_arguments(name, arguments, attributes):

    def valid_argument(name, argument, condition):
        if issubclass(condition, Model):
            valid_arguments(name, argument, condition._get_properties())
        elif not isinstance(argument, condition):
            raise ArgumentKeyError("argument {} was not of the type {}".format(name, condition))
        return True

    for key, attr in attributes.items():
        next_name = "{}.{}".format(name, key)
        if attr.optional:
            if key in arguments:
                valid_argument(next_name, arguments[key], attr.attr_type)
        elif not attr.optional and key not in arguments:
            raise ArgumentKeyError("argument {} was not detected.".format(next_name))
        else:
            valid_argument(next_name, arguments[key], attr.attr_type)

    return True
