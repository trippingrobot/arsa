import pytest
from unittest.mock import MagicMock
from werkzeug.exceptions import BadRequest

from arsa.model import Model, Attribute, ListAttribute
from arsa.model import valid_arguments
from arsa.exceptions import ArgumentKeyError

class FooModel(Model):
    name = Attribute(str)

class BarModel(Model):
    name = Attribute(str)

class FooBarsModel(Model):
    foos = ListAttribute(typeof=FooModel)

def test_model_attribute_inheritance():
    model = FooModel(name='bar')
    model2 = BarModel(**model.attributes)

    assert model.name == 'bar'
    assert model2.name == 'bar'

def test_list_attribute():
    foo = FooModel(name='bar')
    model = FooBarsModel(foos=[foo])
    assert len(model.foos) == 1
    assert model.foos[0].name == 'bar'

    conditions = {
        'foobars': Attribute(FooBarsModel)
    }
    arguments = {
        'foobars':{
            'foos':[
                {
                    'name':'bar'
                }
            ]
        }
    }

    valid_arguments(__name__, arguments, conditions)

def test__invalid_list_attribute():
    conditions = {
        'foobars': Attribute(FooBarsModel)
    }
    arguments = {
        'foobars':{
            'foos':[
                {
                    'bad':'bar'
                }
            ]
        }
    }

    with pytest.raises(ArgumentKeyError):
        valid_arguments(__name__, arguments, conditions)

def test_raw_list_attribute():

    model = FooBarsModel(**{'foos':[{'name':'bar'}]})
    assert len(model.foos) == 1
    assert model.foos[0].name == 'bar'


    conditions = {
        'foobars': Attribute(FooBarsModel)
    }
    arguments = {
        'foobars':{
            'foos':[
                {
                    'name':'bar'
                }
            ]
        }
    }

    valid_arguments(__name__, arguments, conditions)
