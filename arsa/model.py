""" model.py """
from six import add_metaclass
from inspect import getmembers

from .exceptions import ArgumentKeyError

class Attribute(object):

    def __init__(self, attr_type, optional=False, attr_name=None):
        self.attr_type = attr_type
        self.optional = optional
        self.attr_name = attr_name

    def __get__(self, instance, owner):
        return instance.attribute_values.get(self.attr_name, None)

    def __set__(self, instance, value):
        instance.attribute_values[self.attr_name] = value


class ModelMeta(type):
    def __init__(cls, name, bases, attrs):
        super(ModelMeta, cls).__init__(name, bases, attrs)
        ModelMeta._initialize_attributes(cls)

    @staticmethod
    def _initialize_attributes(cls):
        cls._attributes = {}
        for name, attribute in getmembers(cls, lambda attr: isinstance(attr, Attribute)):
            attribute.attr_name = name
            cls._attributes[name] = attribute

@add_metaclass(ModelMeta)
class Model(object):
    """ Abstract class to wrap custom object attributes """

    def __init__(self, **attributes):
        self.attribute_values = {}
        self._set_attributes(**attributes)

    @property
    def attributes(self):
        """ Get defined attribute values """
        return self.attribute_values

    def _set_attributes(self, **attributes):
        """
        Sets the attributes for this object
        """
        for attr_name, attr_value in attributes.items():
            if attr_name not in self._get_attributes():
                raise ValueError("Attribute {0} specified does not exist".format(attr_name))

            attr = self._get_attributes().get(attr_name)
            if issubclass(attr.attr_type, Model):
                setattr(self, attr_name, attr.attr_type(**attr_value))
            else:
                setattr(self, attr_name, attr_value)

    @classmethod
    def _get_attributes(cls):
        """ Return a dict of the models attributes """
        return cls._attributes

def valid_arguments(name, arguments, attributes):

    def valid_argument(name, argument, condition):
        if issubclass(condition, Model):
            valid_arguments(name, argument, condition._get_attributes())
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
