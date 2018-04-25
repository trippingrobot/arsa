from functools import singledispatch
from werkzeug.exceptions import HTTPException
from werkzeug.utils import escape
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


def redirect(location, headers=None, code=302, Response=None):
    """Returns a response object (a WSGI application) that, if called,
    redirects the client to the target location.  Supported codes are 301,
    302, 303, 305, and 307.  300 is not supported because it's not a real
    redirect and 304 because it's the answer for a request with a request
    with defined If-Modified-Since headers.
    .. versionadded:: 0.6
       The location can now be a unicode string that is encoded using
       the :func:`iri_to_uri` function.
    .. versionadded:: 0.10
        The class used for the Response object can now be passed in.
    :param location: the location the response should redirect to.
    :param code: the redirect status code. defaults to 302.
    :param class Response: a Response class to use when instantiating a
        response. The default is :class:`werkzeug.wrappers.Response` if
        unspecified.
    """
    if Response is None:
        from werkzeug.wrappers import Response

    display_location = escape(location)
    if isinstance(location, str):
        # Safe conversion is necessary here as we might redirect
        # to a broken URI scheme (for instance itms-services).
        from werkzeug.urls import iri_to_uri
        location = iri_to_uri(location, safe_conversion=True)
    response = Response(
        '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n'
        '<title>Redirecting...</title>\n'
        '<h1>Redirecting...</h1>\n'
        '<p>You should be redirected automatically to target URL: '
        '<a href="%s">%s</a>.  If not click the link.' %
        (escape(location), display_location), code, mimetype='text/html', headers=headers)
    response.headers['Location'] = location
    return response
