from arsa import Arsa

@Arsa.route("/users")
def list_users():
    """ Get users """
    return [{'id':'124', 'name':'Bob Star', 'email':'bob@star.io'}]

@Arsa.route("/users", methods=['POST'])
@Arsa.required(name=str)
@Arsa.optional(email=str)
def create_user(name, **optional_kwargs):
    """ Create user if client is authenticated """
    email = optional_kwargs['email'] if 'email' in optional_kwargs else None
    return {'id':'124', 'name':name, 'email':email}

@Arsa.route("/accounts/<account_id>")
def get_account(account_id):
    """ Get account with params """
    return [{'id':account_id, 'name':'Acme Inc.', 'email':'support@acme.io'}]

@Arsa.route("/accounts", methods=['POST'])
@Arsa.token_required()
@Arsa.required(name=str)
def create_account(name):
    """ Create account and make sure 'name' parameter is passed as a string """
    return {'id':'124', 'name':name}
