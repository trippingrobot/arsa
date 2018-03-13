from functools import singledispatch

from .model import Model
from .response import AWSResponse

@singledispatch
def to_serializable(val):
    """Used by default."""
    return str(val)

@to_serializable.register(Model)
def ts_model(val):
    """Used if *val* is an instance of our Model class."""
    return val.attribute_values

@to_serializable.register(AWSResponse)
def ts_aws_response(val):
    """Used if *val* is an instance of our AWSResponse class."""
    return {
        "statusCode": val.status_code,
        "body": '{"name":"test"}'
    }
