from werkzeug.local import LocalProxy, LocalStack
from functools import partial

_request_ctx_err_msg = '''\
    Working outside of request context.
    This typically means that you attempted to use functionality that needed
    an active HTTP request.  Consult the documentation on testing for
    information about how to avoid this problem.\
'''

def _lookup_req_object(name):
    top = _request_ctx_stack.top
    if top is None:
        raise RuntimeError(_request_ctx_err_msg)
    return getattr(top, name)

# context locals
_request_ctx_stack = LocalStack()

request = LocalProxy(partial(_lookup_req_object, 'request'))
g = LocalProxy(partial(_lookup_req_object, 'g'))
