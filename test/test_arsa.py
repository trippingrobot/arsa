import pytest
from unittest.mock import MagicMock
from werkzeug.exceptions import NotFound

from arsa_sdk import Arsa

@pytest.fixture(autouse=True)
def empty():
    yield
    #Reset the Arsa singleton for each test
    Arsa.empty()

def test_invalid_route():
    with pytest.raises(NotFound):
        Arsa.serve('/bad', 'GET')

def test_get_route():
    func = MagicMock(return_value='response')
    Arsa.route('/foobar')(func)
    response = Arsa.serve('/foobar', 'GET')
    assert response == 'response'

def test_get_route_with_slug():
    func = MagicMock(side_effect=lambda slug: slug)
    Arsa.route('/foobar/<slug>')(func)
    response = Arsa.serve('/foobar/bar', 'GET')
    assert response == 'bar'

def test_get_route_with_mult_slugs():
    func = MagicMock(side_effect=lambda slug, slug2: slug + slug2)
    Arsa.route('/foobar/<slug>/<slug2>')(func)
    response = Arsa.serve('/foobar/bar/boo', 'GET')
    assert response == 'barboo'

def test_get_route_with_invalid_slug():
    func = MagicMock(side_effect=lambda slug: slug)
    Arsa.route('/foobar/<int:slug>')(func)
    with pytest.raises(NotFound):
        Arsa.serve('/foobar/bar', 'GET')

def test_validate_route():
    func = MagicMock(side_effect=lambda **kwargs: kwargs['name'])
    Arsa.route('/val')(Arsa.required(name=str)(func))
    response = Arsa.serve('/val', 'GET', **{'name':'Bob'})
    assert response == 'Bob'

def test_invalid_route_value():
    func = MagicMock(side_effect=lambda **kwargs: kwargs['name'])
    Arsa.route('/val')(Arsa.required(name=str)(func))
    with pytest.raises(ValueError):
        Arsa.serve('/val', 'GET', **{'name':123})

def test_optional_route_value():
    func = MagicMock(return_value='response')
    Arsa.route('/val')(Arsa.optional(name=str)(func))
    response = Arsa.serve('/val', 'GET')
    assert response == 'response'

def test_optional_invalid_route_value():
    func = MagicMock(side_effect=lambda **kwargs: kwargs['name'])
    Arsa.route('/val')(Arsa.optional(name=str)(func))
    with pytest.raises(ValueError):
        Arsa.serve('/val', 'GET', **{'name':123})

def test_get_route_with_auth():
    func = MagicMock(return_value='response')
    Arsa.route('/foobar')(Arsa.token_required()(func))
    response = Arsa.serve('/foobar', 'GET', token="1234")
    assert response == 'response'

def test_get_route_without_auth():
    func = MagicMock(return_value='response')
    Arsa.route('/foobar')(Arsa.token_required()(func))
    with pytest.raises(ValueError):
        Arsa.serve('/foobar', 'GET')
