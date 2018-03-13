import pytest
import json
import os
from unittest.mock import MagicMock
from werkzeug.test import Client
from werkzeug.wrappers import Response
from arsa import Arsa
from arsa.model import Model, Attribute


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

def test_get_route_with_auth(app):
    func = MagicMock(testfunc, return_value='response')
    app.route('/foobar')(app.token_required()(func))

    client = Client(app.create_app(), response_wrapper=Response)
    response = client.get('/foobar', headers={"x-api-token":"1234"})
    assert response.status_code == 200
    assert response.data == b'"response"'

def test_get_route_without_auth(app):
    func = MagicMock(testfunc, return_value='response')
    app.route('/foobar')(app.token_required()(func))

    client = Client(app.create_app(), response_wrapper=Response)
    response = client.get('/foobar')
    assert response.status_code == 401

def test_token_bypass(app):
    func = MagicMock(testfunc, return_value='response')
    app.route('/foobar')(app.token_required()(func))

    client = Client(app.create_app(check_token=False), response_wrapper=Response)
    response = client.get('/foobar')
    assert response.status_code == 200
    assert response.data == b'"response"'

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
    event = json.load(open(os.path.join(os.path.dirname(__file__), 'requests/api_gateway_proxy.json')))

    response = app.handle(event, {})
    print(response)
    decode = json.loads(response)
    assert decode['statusCode'] == 200
    assert decode['body'] == 'response'

def test_handler2(app):
    func = MagicMock(testfunc, return_value='response')
    app.route('/users')(func)
    event = json.load(open(os.path.join(os.path.dirname(__file__), 'requests/api_gateway_proxy.json')))

    response = app.handle(event, {})
    print(response)
    decode = json.loads(response)
    assert decode['statusCode'] == 200
    assert decode['body'] == 'response'
