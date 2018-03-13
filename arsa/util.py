from functools import singledispatch

from .model import Model

@singledispatch
def to_serializable(val):
    """Used by default."""
    return str(val)

@to_serializable.register(Model)
def ts_model(val):
    """Used if *val* is an instance of our Model class."""
    return val.attribute_values
