from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

import pytest

from typemapping.typemapping import get_field_type

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


class DerivedInit(InitModel):
    def __init__(self, a: str, b: int, c: bool):
        super().__init__(a, b)
        self.c = c


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


@dataclass
class DataClass(Derived):
    name: str


@dataclass
class DataBase:
    name: str


@dataclass
class DataDerived(DataBase):
    age: int


class BaseModel:
    base_field: str = "base_value"


class ExtendedModel(BaseModel):
    extended_field: int = 10

    def __init__(self, dynamic_value: str) -> None:
        self.dynamic_value = dynamic_value

    @property
    def computed_field(self) -> str:
        return f"computed_{self.dynamic_value}"

    def method_field(self) -> str:
        return f"method_{self.dynamic_value}"


@pytest.mark.parametrize(
    "cls, field, expected_type",
    [
        (Derived, "base", int),
        (Derived, "mid", str),
        (Derived, "derived", float),
        (InitModel, "a", str),
        (InitModel, "b", int),
        (DerivedInit, "a", str),
        (DerivedInit, "b", int),
        (DerivedInit, "c", bool),
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
        (DataClass, "base", int),
        (DataClass, "mid", str),
        (DataClass, "derived", float),
        (DataClass, "name", str),
        (DataBase, "name", str),
        (DataDerived, "name", str),
        (DataDerived, "age", int),
        (BaseModel, "base_field", str),
        (ExtendedModel, "base_field", str),
        (ExtendedModel, "extended_field", int),
        (ExtendedModel, "dynamic_value", str),
        (ExtendedModel, "computed_field", str),
        (ExtendedModel, "method_field", str),
    ],
)
def test_get_field_type_(cls, field, expected_type):
    typ = get_field_type(cls, field)
    if expected_type is Any:
        assert typ is not None
    else:
        assert typ == expected_type or (
            isinstance(typ, str) and typ == "User"
        )  # For unresolved forward ref
