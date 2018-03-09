import pytest
import json
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
def empty():
    yield
    #Reset the Arsa singleton for each test
    Arsa.empty()

def test_invalid_route():
    client = Client(Arsa.create_app(), response_wrapper=Response)
    response = client.get('/bad/path')
    assert response.status_code == 404

def test_bad_json_route():
    func = MagicMock(testfunc, return_value='response')
    Arsa.route('/foobar')(func)
    client = Client(Arsa.create_app(), response_wrapper=Response)
    response = client.get('/foobar', data='{}}')
    assert response.status_code == 400

def test_get_route():
    func = MagicMock(testfunc, return_value='response')
    Arsa.route('/foobar')(func)

    client = Client(Arsa.create_app(), response_wrapper=Response)
    response = client.get('/foobar')
    assert response.status_code == 200
    assert response.data == b'"response"'

def test_get_route_with_slug():
    func = MagicMock(testfunc, side_effect=lambda slug: slug)
    Arsa.route('/foobar/<slug>')(func)

    client = Client(Arsa.create_app(), response_wrapper=Response)
    response = client.get('/foobar/bar')
    assert response.status_code == 200
    assert response.data == b'"bar"'

def test_get_route_with_mult_slugs():
    func = MagicMock(testfunc, side_effect=lambda slug, slug2: slug + slug2)
    Arsa.route('/foobar/<slug>/<slug2>')(func)

    client = Client(Arsa.create_app(), response_wrapper=Response)
    response = client.get('/foobar/bar/boo')
    assert response.status_code == 200
    assert response.data == b'"barboo"'

def test_get_route_with_invalid_slug():
    func = MagicMock(testfunc, side_effect=lambda slug: slug)
    Arsa.route('/foobar/<int:slug>')(func)

    client = Client(Arsa.create_app(), response_wrapper=Response)
    response = client.get('/foobar/bar')
    assert response.status_code == 404

def test_validate_route():
    func = MagicMock(testfunc, side_effect=lambda **kwargs: kwargs['name'])
    Arsa.route('/val')(Arsa.required(name=str)(func))

    client = Client(Arsa.create_app(), response_wrapper=Response)
    response = client.get('/val', data=json.dumps({'name':'Bob'}))
    assert response.status_code == 200
    assert response.data == b'"Bob"'

def test_invalid_route_value():
    func = MagicMock(testfunc, side_effect=lambda **kwargs: kwargs['name'])
    Arsa.route('/val')(Arsa.required(name=str)(func))

    client = Client(Arsa.create_app(), response_wrapper=Response)
    response = client.get('/val', data={'name':'Bob'})
    assert response.status_code == 400

def test_optional_route_value():
    func = MagicMock(testfunc, return_value='response')
    Arsa.route('/val')(Arsa.optional(name=str)(func))

    client = Client(Arsa.create_app(), response_wrapper=Response)
    response = client.get('/val')
    assert response.status_code == 200
    assert response.data == b'"response"'

def test_optional_invalid_route_value():
    func = MagicMock(testfunc, side_effect=lambda **kwargs: kwargs['name'])
    Arsa.route('/val')(Arsa.optional(name=str)(func))

    client = Client(Arsa.create_app(), response_wrapper=Response)
    response = client.get('/val', data=json.dumps({'name':123}))
    assert response.status_code == 400

def test_get_route_with_auth():
    func = MagicMock(testfunc, return_value='response')
    Arsa.route('/foobar')(Arsa.token_required()(func))

    client = Client(Arsa.create_app(), response_wrapper=Response)
    response = client.get('/foobar', headers={"x-api-token":"1234"})
    assert response.status_code == 200
    assert response.data == b'"response"'

def test_get_route_without_auth():
    func = MagicMock(testfunc, return_value='response')
    Arsa.route('/foobar')(Arsa.token_required()(func))

    client = Client(Arsa.create_app(), response_wrapper=Response)
    response = client.get('/foobar')
    assert response.status_code == 401

def test_token_bypass():
    func = MagicMock(testfunc, return_value='response')
    Arsa.route('/foobar')(Arsa.token_required()(func))

    client = Client(Arsa.create_app(check_token=False), response_wrapper=Response)
    response = client.get('/foobar')
    assert response.status_code == 200
    assert response.data == b'"response"'

def test_validate_route_with_model():
    func = MagicMock(testfunc, side_effect=lambda tester: tester.name)
    Arsa.route('/val')(Arsa.required(tester=SampleModel)(func))

    client = Client(Arsa.create_app(), response_wrapper=Response)
    response = client.get('/val', data=json.dumps({'tester':{'name':'Bob'}}))
    assert response.status_code == 200
    assert response.data == b'"Bob"'
