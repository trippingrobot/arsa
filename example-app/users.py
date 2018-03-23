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
    """ Create user if client is authenticated """
    email = optional_kwargs['email'] if 'email' in optional_kwargs else None
    return {'id':'124', 'name':name, 'email':email}

@app.route("/accounts/<account_id>")
def get_account(account_id):
    """ Get account with params """
    return [{'id':account_id, 'name':'Acme Inc.', 'email':'support@acme.io'}]

@app.route("/accounts", methods=['POST'])
@app.required(name=str, owner=Person)
@app.optional(partner=Person)
def create_account(name, owner, **optional_kwargs):
    """ Create account and make sure 'name' parameter is passed as a string """
    return {'id':'124', 'name':name, 'owner': owner, 'partner': optional_kwargs.get('partner', None)}


@app.authorizer
def custom_auth(auth_event):
    # TODO: Check for authorization
    principal_id = auth_event['authorizationToken']
    arn = auth_event['methodArn']
    return Policy(principal_id, arn, allow=True) # OR DenyPolicy(principal_id, context)


handler = app.handler
authorize = app.authorize
