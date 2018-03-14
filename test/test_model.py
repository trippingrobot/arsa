import pytest
from unittest.mock import MagicMock
from werkzeug.exceptions import BadRequest

from arsa.model import Model, Attribute

class FooModel(Model):
    name = Attribute(str)

class BarModel(Model):
    name = Attribute(str)

def test_model_attribute_inheritance():
    model = FooModel(name='bar')
    model2 = BarModel(**model.attributes)

    assert model.name == 'bar'
    assert model2.name == 'bar'
