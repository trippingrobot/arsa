from functools import singledispatch
from werkzeug.exceptions import HTTPException
from .model import Model
from .exceptions import Redirect

@singledispatch
def to_serializable(val):
    """Used by default."""
    return str(val)

@to_serializable.register(Model)
def ts_model(val):
    """Used if *val* is an instance of our Model class."""
    return val.attributes

@to_serializable.register(HTTPException)
def ts_model(val):
    """Used if *val* is an instance of our HTTPException class."""
    return {
        "error": val.name,
        "description": val.description
    }

@to_serializable.register(Redirect)
def ts_model(val):
    """Used if *val* is an instance of our HTTPException class."""
    return {
        "error": val.location
    }
