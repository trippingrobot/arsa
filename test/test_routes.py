import pytest
from unittest.mock import MagicMock
from werkzeug.exceptions import BadRequest

from arsa.routes import Route
from arsa.model import Model, Attribute

class TestModel(Model):
    name = Attribute(str)

class ComplexTestModel(Model):
    test = Attribute(TestModel)

def test_required_model_route():
    func = MagicMock(side_effect=lambda obj: obj.name)
    route = Route(func)

    route.add_validation(obj=TestModel)
    assert route.has_valid_arguments({'obj': {'name':'foobar'}})

def test_complex_route():
    func = MagicMock(return_value=True)
    route = Route(func)

    route.add_validation(obj=ComplexTestModel)
    assert route.has_valid_arguments({'obj': {'test':{'name':'foobar'}}})

def test_optional_model_route():
    func = MagicMock(return_value=True)
    route = Route(func)

    route.add_validation(True, obj=TestModel)

    with pytest.raises(BadRequest):
        route.has_valid_arguments({'obj': {}})
