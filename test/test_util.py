import pytest
import json

from arsa.util import to_serializable
from arsa.model import Model, Attribute

class SampleModel(Model):
    name = Attribute(str)
    phone = Attribute(str, optional=True)

class ComplexTestModel(Model):
    test = Attribute(SampleModel)

def test_serialize():
    model = SampleModel(name='Foo', phone='1234567890')
    raw = json.dumps(model, default=to_serializable)
    assert raw == '{"name": "Foo", "phone": "1234567890"}'

def test_serialize_complex():
    model = ComplexTestModel(test={'name':'Foo', 'phone':'1234567890'})
    raw = json.dumps(model, default=to_serializable)
    assert raw == '{"test": {"name": "Foo", "phone": "1234567890"}}'
