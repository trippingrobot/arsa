from arsa import Arsa
from arsa.model import Model, Attribute
from arsa.policy import Policy

class Person(Model):
    name = Attribute(str)
    phone = Attribute(int, optional=True)

app = Arsa()

@app.route("/users")
def list_users():
    """ Get users """
    return [{'id':'124', 'name':'Bob Star', 'email':'ed@arsa.io'}]

@app.route("/users", methods=['POST'])
@app.required(name=str)
@app.optional(email=str)
def create_user(name, **optional_kwargs):
    """ Create user """
    email = optional_kwargs['email'] if 'email' in optional_kwargs else None
    return {'id':'124', 'name':name, 'email':email}

@app.route("/account", inject_request=True)
def get_account(_req):
    """ Get account with params """
    print(_req.environ['aws.requestContext'])
    principal_id = _req.environ['aws.requestContext'].authorizer.principalId
    return {'id':principal_id, 'name':'Acme Inc.', 'email':'support@acme.io'}

@app.route("/accounts", methods=['POST'])
@app.required(name=str, owner=Person)
@app.optional(partner=Person)
def create_account(name, owner, **optional_kwargs):
    """ Create account and make sure 'name' parameter is passed as a string """
    return {'id':'124', 'name':name, 'owner': owner, 'partner': optional_kwargs.get('partner', None)}


@app.authorizer()
def custom_auth(auth_event, context):
    # Create base policy from auth event
    policy = Policy(auth_event)

    # Set permission
    policy.allow = (policy.token == 'test_token')

    # Pass value to backend
    policy.principal_id = 'user'

    return policy


handler = app.handler
authorize = app.authorize
