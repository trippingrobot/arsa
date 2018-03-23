import pytest
from unittest.mock import MagicMock
from werkzeug.exceptions import BadRequest

from arsa.routes import Route
from arsa.model import Model, Attribute

def testfunc():
    pass

class SampleModel(Model):
    name = Attribute(str)
    phone = Attribute(str, optional=True)

class ComplexTestModel(Model):
    test = Attribute(SampleModel)

def test_required_model_route():
    func = MagicMock(testfunc, side_effect=lambda obj: obj.name)
    route = Route(func)

    route.add_validation(obj=SampleModel)
    assert route.has_valid_arguments({'obj': {'name':'foobar'}})

def test_complex_route():
    func = MagicMock(testfunc, return_value=True)
    route = Route(func)

    route.add_validation(obj=ComplexTestModel)
    assert route.has_valid_arguments({'obj': {'test':{'name':'foobar'}}})

def test_optional_model_route():
    func = MagicMock(testfunc, return_value=True)
    route = Route(func)

    route.add_validation(True, obj=SampleModel)

    with pytest.raises(BadRequest):
        route.has_valid_arguments({'obj': {}})

def test_decode_complex_model():
    func = MagicMock(testfunc, return_value=True)
    route = Route(func)

    route.add_validation(obj=ComplexTestModel)
    decoded = route.decode_arguments({'obj': {'test':{'name':'foobar'}}})
    assert decoded['obj'].test.name == 'foobar'
    assert decoded['obj'].test.phone is None

def test_reserved_route():
    func = MagicMock(testfunc, return_value=True)
    route = Route(func)

    with pytest.raises(ValueError):
        route.add_validation(query=bool)
