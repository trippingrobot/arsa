from __future__ import print_function
import pytest

from sdk.router import Router
from sdk.exceptions import BadRoute

@Router.route("fake.route")
def fake_route():
    pass

@Router.route("fake.route2")
def fake_route2(foo):
    return foo

def test_invalid_route():
    router = Router()
    with pytest.raises(BadRoute):
        router.serve("bad route")

def test_valid_route():
    router = Router()
    router.serve("fake.route")

def test_invalid_route_with_kwargs():
    router = Router()
    with pytest.raises(TypeError):
        router.serve(**{})

def test_valid_route_with_kwargs():
    router = Router()
    router.serve(**{"route":"fake.route"})

def test_valid_route_with_kwargs_pass():
    router = Router()
    result = router.serve(**{"route":"fake.route2", "foo":"bar"})
    assert result == "bar"
