from dataclasses import dataclass, field

from typing_extensions import Annotated, Dict, List, Optional, Union

from typemapping import (
    NO_DEFAULT,
    VarTypeInfo,
    map_dataclass_fields,
    map_init_field,
    map_model_fields,
)


@dataclass(frozen=True)
class Meta1:
    pass


@dataclass(frozen=True)
class Meta2:
    pass


@dataclass
class SimpleDefault:
    x: int = 10


@dataclass
class WithDefaultFactory:
    y: List[int] = field(default_factory=list)


@dataclass
class NoDefault:
    z: str


@dataclass
class AnnotatedSingle:
    a: Annotated[int, Meta1()] = 5


@dataclass
class AnnotatedMultiple:
    b: Annotated[str, Meta1(), Meta2()] = "hello"


@dataclass
class OptionalNoDefault:
    c: Optional[int]


@dataclass
class OptionalDefaultNone:
    d: Optional[int] = None


@dataclass
class AnnotatedOptional:
    e: Annotated[Optional[str], Meta1()] = None


@dataclass
class WithUnion:
    f: Union[int, str] = 42


@dataclass
class DataClassWithDict:
    data: Dict[str, int] = field(default_factory=Dict)


class ClassSimpleDefault:
    def __init__(self, x: int = 10):
        self.x = x


class ClassAnnotatedMultiple:
    def __init__(self, b: Annotated[str, Meta1(), Meta2()] = "hello"):
        self.b = b


class ClassOptionalNoDefault:
    def __init__(self, c: Optional[int]):
        self.c = c


class ClassWithUnion:
    def __init__(self, f: Union[int, str] = 42):
        self.f = f


class ClassAnnotatedOptional:
    def __init__(self, e: Annotated[Optional[str], Meta1()] = None):
        self.e = e


class InitClassWithDict:
    def __init__(self, data: Dict[str, int] = {}):
        self.data = data


class InitClass:
    def __init__(
        self, x: int, y: Optional[str] = "abc", z: Annotated[float, "meta"] = 3.14
    ):
        self.x, self.y, self.z = x, y, z


class OnlyClassSimple:
    x: int = 10


class OnlyClassAnnotated:
    a: Annotated[int, Meta1()] = 5


class OnlyClassAnnotatedMultiple:
    b: Annotated[str, Meta1(), Meta2()] = "hello"


class OnlyClassOptional:
    c: Optional[int]


class OnlyClassOptionalDefaultNone:
    d: Optional[int] = None


class OnlyClassAnnotatedOptional:
    e: Annotated[Optional[str], Meta1()] = None


class OnlyClassUnion:
    f: Union[int, str] = 42


class OnlyClassNoDefault:
    g: str


class ModelClassWithDict:
    data: Dict[str, int] = {}


@dataclass
class DataClass:
    x: int
    y: Optional[str] = "abc"
    z: Annotated[float, "meta"] = 3.14


class ModelClass:
    x: int = 1
    y: Union[str, None] = "default"
    z: Annotated[float, "meta"] = 3.14


# Helper functions for pytest tests
def assert_vartypeinfo(
    vti: VarTypeInfo, name: str, expected_type: type, expected_default: object
):
    assert vti.name == name
    assert vti.basetype == expected_type
    assert (
        vti.default == expected_default
        if expected_default is not NO_DEFAULT
        else vti.default is NO_DEFAULT
    )
    assert vti.istype(expected_type)
    assert vti.isequal(expected_type)


def assert_dict_like(vti: VarTypeInfo):
    assert vti.istype(Dict[str, int])
    assert vti.args == (str, int)


def test_map_dataclass_fields() -> None:
    args = map_dataclass_fields(SimpleDefault)
    assert_vartypeinfo(args[0], "x", int, 10)

    args = map_dataclass_fields(WithDefaultFactory)
    assert args[0].name == "y"
    assert args[0].basetype == List[int]

    args = map_dataclass_fields(NoDefault)
    assert_vartypeinfo(args[0], "z", str, NO_DEFAULT)

    args = map_dataclass_fields(AnnotatedSingle)
    assert args[0].name == "a"
    assert args[0].extras[0].__class__.__name__ == "Meta1"

    args = map_dataclass_fields(AnnotatedMultiple)
    assert len(args[0].extras) == 2


def test_map_init_field() -> None:
    args = map_init_field(ClassSimpleDefault)
    assert_vartypeinfo(args[0], "x", int, 10)

    args = map_init_field(ClassOptionalNoDefault)
    assert args[0].name == "c"
    assert args[0].origin == Union

    args = map_init_field(ClassAnnotatedOptional)
    assert args[0].name == "e"
    assert args[0].origin == Union
    assert args[0].default is None


def test_map_model_fields() -> None:
    args = map_model_fields(ModelClass)
    assert_vartypeinfo(args[0], "x", int, 1)
    assert args[1].name == "y"
    assert args[1].origin == Union
    assert args[2].name == "z"
    assert args[2].extras[0] == "meta"


def test_map_dataclass_edge_cases() -> None:
    args = map_dataclass_fields(AnnotatedOptional)
    assert args[0].name == "e"
    assert args[0].default is None

    args = map_dataclass_fields(WithUnion)
    assert args[0].name == "f"
    assert args[0].origin == Union


def test_map_init_field_advanced() -> None:
    args = map_init_field(InitClass)
    assert len(args) == 3
    assert args[0].name == "x"
    assert args[0].default is NO_DEFAULT
    assert args[1].default == "abc"
    assert args[2].extras[0] == "meta"


def test_map_dataclass_fields_advanced() -> None:
    args = map_dataclass_fields(DataClass)
    assert args[0].name == "x"
    assert args[1].default == "abc"
    assert args[2].extras[0] == "meta"


def test_model_fields_extras() -> None:
    args = map_model_fields(ModelClass)
    for vti in args:
        assert isinstance(vti, VarTypeInfo)


def test_map_dataclass_fields_with_dict() -> None:
    args = map_dataclass_fields(DataClassWithDict)
    assert len(args) == 1
    assert args[0].name == "data"
    assert_dict_like(args[0])
    assert args[0].default == Dict


def test_map_init_field_with_dict() -> None:
    args = map_init_field(InitClassWithDict)
    assert len(args) == 1
    assert args[0].name == "data"
    assert_dict_like(args[0])
    assert args[0].default == {}


def test_map_model_fields_with_dict() -> None:
    args = map_model_fields(ModelClassWithDict)
    assert len(args) == 1
    assert args[0].name == "data"
    assert_dict_like(args[0])
    assert args[0].default == {}
