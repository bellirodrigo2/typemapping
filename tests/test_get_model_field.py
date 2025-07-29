from datetime import datetime
from typing import TYPE_CHECKING, Any

import pytest

from typemapping.typemapping import get_field_type_

if TYPE_CHECKING:
    User = Any

# Simulação de múltiplos casos

class Base:
    base: int

class Middle(Base):
    mid: str

class Derived(Middle):
    derived: float

class InitModel:
    def __init__(self, a: str, b: int):
        self.a = a
        self.b = b

class MixedModel:
    mixed: int

    def __init__(self, x: float):
        self.x = x

class PropertyWithReturn:
    @property
    def prop(self) -> datetime:
        return datetime.now()

class PropertyNoReturn:
    @property
    def prop(self):
        return "no return hint"

class MethodWithReturn:
    def call(self) -> bool:
        return True

class MethodNoReturn:
    def call(self):
        return None

class NoAnnotations:
    pass

class FallbackModel:
    field = None  # No annotation

class ForwardRefModel:
    ref: "User"

class Nested:
    class Inner:
        name: str

class BuiltInWrapper:
    def __init__(self, items: list):
        self.items = items


@pytest.mark.parametrize(
    "cls, field, expected_type",
    [
        (Derived, "base", int),
        (Derived, "mid", str),
        (Derived, "derived", float),
        (InitModel, "a", str),
        (InitModel, "b", int),
        (MixedModel, "mixed", int),
        (MixedModel, "x", float),
        (PropertyWithReturn, "prop", datetime),
        (PropertyNoReturn, "prop", None),
        (MethodWithReturn, "call", bool),
        (MethodNoReturn, "call", None),
        (NoAnnotations, "x", None),
        (FallbackModel, "field", None),
        (ForwardRefModel, "ref", Any),  # might remain unresolved string in 3.8
        (Nested.Inner, "name", str),
        (BuiltInWrapper, "items", list),
        (BuiltInWrapper, "missing", None),
    ]
)
def test_get_field_type_(cls, field, expected_type):
    typ = get_field_type_(cls, field)
    if expected_type is Any:
        assert typ is not None
    else:
        assert typ == expected_type or (
            isinstance(typ, str) and typ == "User"
        )  # For unresolved forward ref
