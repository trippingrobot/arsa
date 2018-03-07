import pytest
import json
from unittest.mock import MagicMock
from werkzeug.exceptions import NotFound
from werkzeug.test import Client
from werkzeug.wrappers import Response
from arsa_sdk import Arsa


@pytest.fixture(autouse=True)
def empty():
    yield
    #Reset the Arsa singleton for each test
    Arsa.empty()

def test_invalid_route():
    client = Client(Arsa.create_app())
    with pytest.raises(NotFound):
        client.open('/bad/path')

def test_get_route():
    func = MagicMock(return_value='response')
    Arsa.route('/foobar')(func)

    client = Client(Arsa.create_app(), response_wrapper=Response)
    response = client.get('/foobar')
    assert response.status_code == 200
    assert response.data == b'"response"'

def test_get_route_with_slug():
    func = MagicMock(side_effect=lambda slug: slug)
    Arsa.route('/foobar/<slug>')(func)

    client = Client(Arsa.create_app(), response_wrapper=Response)
    response = client.get('/foobar/bar')
    assert response.status_code == 200
    assert response.data == b'"bar"'

def test_get_route_with_mult_slugs():
    func = MagicMock(side_effect=lambda slug, slug2: slug + slug2)
    Arsa.route('/foobar/<slug>/<slug2>')(func)

    client = Client(Arsa.create_app(), response_wrapper=Response)
    response = client.get('/foobar/bar/boo')
    assert response.status_code == 200
    assert response.data == b'"barboo"'

def test_get_route_with_invalid_slug():
    func = MagicMock(side_effect=lambda slug: slug)
    Arsa.route('/foobar/<int:slug>')(func)

    client = Client(Arsa.create_app(), response_wrapper=Response)
    with pytest.raises(NotFound):
        client.get('/foobar/bar')

def test_validate_route():
    func = MagicMock(side_effect=lambda **kwargs: kwargs['name'])
    Arsa.route('/val')(Arsa.required(name=str)(func))

    client = Client(Arsa.create_app(), response_wrapper=Response)
    response = client.get('/val', data=json.dumps({'name':'Bob'}))
    assert response.status_code == 200
    assert response.data == b'"Bob"'

def test_invalid_route_value():
    func = MagicMock(side_effect=lambda **kwargs: kwargs['name'])
    Arsa.route('/val')(Arsa.required(name=str)(func))

    client = Client(Arsa.create_app(), response_wrapper=Response)
    with pytest.raises(ValueError):
        client.get('/val', data={'name':'Bob'})

def test_optional_route_value():
    func = MagicMock(return_value='response')
    Arsa.route('/val')(Arsa.optional(name=str)(func))

    client = Client(Arsa.create_app(), response_wrapper=Response)
    response = client.get('/val')
    assert response.status_code == 200
    assert response.data == b'"response"'

def test_optional_invalid_route_value():
    func = MagicMock(side_effect=lambda **kwargs: kwargs['name'])
    Arsa.route('/val')(Arsa.optional(name=str)(func))

    client = Client(Arsa.create_app(), response_wrapper=Response)
    with pytest.raises(ValueError):
        client.get('/val', data=json.dumps({'name':123}))

def test_get_route_with_auth():
    func = MagicMock(return_value='response')
    Arsa.route('/foobar')(Arsa.token_required()(func))

    client = Client(Arsa.create_app(), response_wrapper=Response)
    response = client.get('/foobar', headers={"x-api-token":"1234"})
    assert response.status_code == 200
    assert response.data == b'"response"'

def test_get_route_without_auth():
    func = MagicMock(return_value='response')
    Arsa.route('/foobar')(Arsa.token_required()(func))

    client = Client(Arsa.create_app(), response_wrapper=Response)
    with pytest.raises(ValueError):
        client.get('/foobar')
