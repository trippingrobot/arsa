from werkzeug.exceptions import HTTPException
from werkzeug.datastructures import EnvironHeaders

class ArgumentKeyError(ValueError): pass
class NoCredentailsFoundError(Exception): pass

class Redirect(HTTPException):
    code = 302
    def __init__(self, location):
        super(Redirect, self).__init__()
        self.location = location

    def get_headers(self, environ=None):
        headers = []
        if environ:
            headers = list(EnvironHeaders(environ))

        headers.append(('Location', self.location))

        return headers
