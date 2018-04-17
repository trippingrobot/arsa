import pytest
import json
import os

from unittest.mock import MagicMock
from werkzeug.test import Client
from werkzeug.wrappers import Response
from arsa import Arsa
from arsa.model import Model, Attribute, ListType
from arsa.policy import Policy
from arsa.exceptions import Redirect
from arsa.globals import request, g

class SampleModel(Model):
    name = Attribute(str)

def testfunc():
    pass

@pytest.fixture(autouse=True)
def app():
    """ Create app instance for future default routes """
    return Arsa()

def test_invalid_route(app):
    client = Client(app.create_app(), response_wrapper=Response)
    response = client.get('/bad/path')
    assert response.status_code == 404

def test_bad_json_route(app):
    func = MagicMock(testfunc, return_value='response')
    app.route('/foobar')(func)
    client = Client(app.create_app(), response_wrapper=Response)
    response = client.get('/foobar', data='{}}')
    assert response.status_code == 400

def test_get_route(app):
    func = MagicMock(testfunc, return_value='response')
    app.route('/foobar')(func)

    client = Client(app.create_app(), response_wrapper=Response)
    response = client.get('/foobar')
    assert response.status_code == 200
    assert response.data == b'"response"'

def test_get_route_with_slug(app):
    func = MagicMock(testfunc, side_effect=lambda slug: slug)
    app.route('/foobar/<slug>')(func)

    client = Client(app.create_app(), response_wrapper=Response)
    response = client.get('/foobar/bar')
    assert response.status_code == 200
    assert response.data == b'"bar"'

def test_get_route_with_mult_slugs(app):
    func = MagicMock(testfunc, side_effect=lambda slug, slug2: slug + slug2)
    app.route('/foobar/<slug>/<slug2>')(func)

    client = Client(app.create_app(), response_wrapper=Response)
    response = client.get('/foobar/bar/boo')
    assert response.status_code == 200
    assert response.data == b'"barboo"'

def test_get_route_with_invalid_slug(app):
    func = MagicMock(testfunc, side_effect=lambda slug: slug)
    app.route('/foobar/<int:slug>')(func)

    client = Client(app.create_app(), response_wrapper=Response)
    response = client.get('/foobar/bar')
    assert response.status_code == 404

def test_validate_route(app):
    func = MagicMock(testfunc, side_effect=lambda **kwargs: kwargs['name'])
    app.route('/val')(app.required(name=str)(func))

    client = Client(app.create_app(), response_wrapper=Response)
    response = client.get('/val', data=json.dumps({'name':'Bob'}))
    assert response.status_code == 200
    assert response.data == b'"Bob"'

def test_invalid_route_value(app):
    func = MagicMock(testfunc, side_effect=lambda **kwargs: kwargs['name'])
    app.route('/val')(app.required(name=str)(func))

    client = Client(app.create_app(), response_wrapper=Response)
    response = client.get('/val', data={'name':'Bob'})
    assert response.status_code == 400


def test_optional_route_value(app):
    func = MagicMock(testfunc, return_value='response')
    app.route('/val')(app.optional(name=str)(func))

    client = Client(app.create_app(), response_wrapper=Response)
    response = client.get('/val')
    assert response.status_code == 200
    assert response.data == b'"response"'

def test_optional_invalid_route_value(app):
    func = MagicMock(testfunc, side_effect=lambda **kwargs: kwargs['name'])
    app.route('/val')(app.optional(name=str)(func))

    client = Client(app.create_app(), response_wrapper=Response)
    response = client.get('/val', data=json.dumps({'name':123}))
    assert response.status_code == 400

def test_auth(app):
    auth_event = {
        'type': 'TOKEN',
        'authorizationToken' : 'test1234',
        'methodArn': 'arn:aws:execute-api:us-west-2:123456789012:ymy8tbxw7b/v1/GET/{proxy+}'
    }

    res = app.authorize(auth_event, {})
    assert res['policyDocument']['Statement'][0]['Effect'] == 'Allow'

def test_custom_auth(app):
    auth_event = {
        'type': 'TOKEN',
        'authorizationToken' : 'test1234',
        'methodArn': 'arn:aws:execute-api:us-west-2:123456789012:ymy8tbxw7b/v1/GET/{proxy+}'
    }

    deny = Policy(auth_event, allow=False, context={'custom_attr':'string'})
    deny.principal_id = 'user'
    func = MagicMock(testfunc, return_value=deny)

    app.authorizer()(func)
    res = app.authorize(auth_event, {})
    assert res['policyDocument']['Statement'][0]['Effect'] == 'Deny'
    assert res['principalId'] == 'user'
    assert res['context']['custom_attr'] == 'string'
    assert res['policyDocument']['Statement'][0]['Resource'] == '*'

def test_validate_route_with_model(app):
    func = MagicMock(testfunc, side_effect=lambda tester: tester.name)
    app.route('/val')(app.required(tester=SampleModel)(func))

    client = Client(app.create_app(), response_wrapper=Response)
    response = client.get('/val', data=json.dumps({'tester':{'name':'Bob'}}))
    assert response.status_code == 200
    assert response.data == b'"Bob"'

def test_handler(app):
    func = MagicMock(testfunc, return_value='response')
    app.route('/users')(func)
    event = json.load(open(os.path.join(os.path.dirname(__file__), 'requests/get_proxy.json')))

    response = app.handler(event, {})
    assert response['statusCode'] == 200
    assert response['body'] == '"response"'

def test_data_handler(app):
    func = MagicMock(testfunc, return_value='response')
    app.route('/users', methods=['POST'])(app.required(name=str)(func))
    event = json.load(open(os.path.join(os.path.dirname(__file__), 'requests/post_proxy.json')))

    response = app.handler(event, {})
    assert response['statusCode'] == 200
    assert response['body'] == '"response"'

def test_error_handler(app):
    func = MagicMock(testfunc, return_value='response')
    app.route('/users', methods=['POST'])(app.required(no=str)(func))
    event = json.load(open(os.path.join(os.path.dirname(__file__), 'requests/post_proxy.json')))

    response = app.handler(event, {})

    assert response['statusCode'] == 400

def test_redirect_handler(app):

    def throw(**args):
        raise Redirect('http://example.com')

    app.route('/users')(throw)
    event = json.load(open(os.path.join(os.path.dirname(__file__), 'requests/get_proxy.json')))

    response = app.handler(event, {})

    print(response)

    assert response['statusCode'] == 302
    assert response['headers']['Location'] == 'http://example.com'

def test_get_route_with_query_params(app):
    func = MagicMock(testfunc, side_effect=lambda **kwargs: request.args['happy'])
    app.route('/foobar')(func)

    client = Client(app.create_app(), response_wrapper=Response)
    response = client.get('/foobar?bob=star&happy=lucky')
    assert response.status_code == 200
    assert response.data == b'"lucky"'

def test_get_route_with_req_query_params(app):
    func = MagicMock(testfunc, side_effect=lambda val: val)
    app.route('/foobar')(app.required(val=str)(func))

    client = Client(app.create_app(), response_wrapper=Response)
    response = client.get('/foobar?val=burger')
    print(response.data)
    assert response.status_code == 200
    assert response.data == b'"burger"'

def test_get_route_with_multi_query_params(app):
    func = MagicMock(testfunc, return_value=['dog', 'cat'])
    app.route('/foobar')(app.required(animal=ListType)(func))

    client = Client(app.create_app(), response_wrapper=Response)
    response = client.get('/foobar?animal=dog&animal=cat')
    print(response.data)
    assert response.status_code == 200
    assert response.data == b'["dog", "cat"]'

def test_global_request_context(app):
    func = MagicMock(testfunc, side_effect=lambda: request.headers['Host'])
    app.route('/foobar')(func)

    client = Client(app.create_app(), response_wrapper=Response)
    response = client.get('/foobar')
    assert response.data == b'"localhost"'

def test_global_map_context(app):

    def func1():
        g.user = 'userface'
        return func2()

    def func2():
        return g.user

    func = MagicMock(testfunc, side_effect=func1)
    app.route('/foobar')(func)

    client = Client(app.create_app(), response_wrapper=Response)
    response = client.get('/foobar')
    assert response.data == b'"userface"'

def test_middleware(app):
    def middleware():
        g.user = 'userface'

    app.add_middleware(middleware)

    func = MagicMock(testfunc, side_effect=lambda: g.user)
    app.route('/foobar')(func)

    client = Client(app.create_app(), response_wrapper=Response)
    response = client.get('/foobar')
    assert response.data == b'"userface"'

def test_html_mime_type(app):
    func = MagicMock(testfunc, return_value='<html><body><p>HI</p></body></html>')
    app.route('/coolwebsite', content_type='application/html')(func)

    client = Client(app.create_app(), response_wrapper=Response)
    response = client.get('/coolwebsite')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/html'
    assert response.data == b'<html><body><p>HI</p></body></html>'
