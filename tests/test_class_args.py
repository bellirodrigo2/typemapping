import unittest
from dataclasses import dataclass, field

from typing_extensions import Annotated, Dict, List, Optional, Union

from typemapping.typemapping import (
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


# --- Definições de classes usadas nos testes --- #

# Dataclasses


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


# Classes com __init__


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
        self.x = x
        self.y = y
        self.z = z


# Classes só com annotations (sem init nem dataclass)


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


class TestMapFieldFunctions(unittest.TestCase):
    def assert_vartypeinfo(
        self, vti: VarTypeInfo, name: str, expected_type: type, expected_default: object
    ):
        self.assertEqual(vti.name, name)
        self.assertEqual(vti.basetype, expected_type)

        if expected_default is NO_DEFAULT:
            self.assertEqual(vti.default, NO_DEFAULT)
        else:
            self.assertEqual(vti.default, expected_default)

        self.assertTrue(vti.istype(expected_type))
        self.assertTrue(vti.isequal(expected_type))

    def assert_dict_like(self, vti: VarTypeInfo):
        self.assertTrue(vti.istype(Dict[str, int]))
        self.assertEqual(vti.args, (str, int))

    def test_map_dataclass_fields(self):
        args = map_dataclass_fields(SimpleDefault)
        self.assert_vartypeinfo(args[0], "x", int, 10)

        args = map_dataclass_fields(WithDefaultFactory)
        self.assertEqual(args[0].name, "y")
        self.assertEqual(args[0].basetype, List[int])

        args = map_dataclass_fields(NoDefault)
        self.assert_vartypeinfo(args[0], "z", str, NO_DEFAULT)

        args = map_dataclass_fields(AnnotatedSingle)
        self.assertEqual(args[0].name, "a")
        self.assertEqual(args[0].extras[0].__class__.__name__, "Meta1")

        args = map_dataclass_fields(AnnotatedMultiple)
        self.assertEqual(len(args[0].extras), 2)

    def test_map_init_field(self):
        args = map_init_field(ClassSimpleDefault)
        self.assert_vartypeinfo(args[0], "x", int, 10)

        args = map_init_field(ClassOptionalNoDefault)
        self.assertEqual(args[0].name, "c")
        self.assertEqual(args[0].origin, Union)

        args = map_init_field(ClassAnnotatedOptional)
        self.assertEqual(args[0].name, "e")
        self.assertEqual(args[0].origin, Union)
        self.assertEqual(args[0].default, None)

    def test_map_model_fields(self):
        args = map_model_fields(ModelClass)
        self.assert_vartypeinfo(args[0], "x", int, 1)
        self.assertEqual(args[1].name, "y")
        self.assertEqual(args[1].origin, Union)
        self.assertEqual(args[2].name, "z")
        self.assertEqual(args[2].extras[0], "meta")

    def test_map_dataclass_edge_cases(self):
        args = map_dataclass_fields(AnnotatedOptional)
        self.assertEqual(args[0].name, "e")
        self.assertEqual(args[0].default, None)

        args = map_dataclass_fields(WithUnion)
        self.assertEqual(args[0].name, "f")
        self.assertEqual(args[0].origin, Union)

    def test_map_init_field_advanced(self):
        args = map_init_field(InitClass)
        self.assertEqual(len(args), 3)
        self.assertEqual(args[0].name, "x")
        self.assertEqual(args[0].default, NO_DEFAULT)
        self.assertEqual(args[1].default, "abc")
        self.assertEqual(args[2].extras[0], "meta")

    def test_map_dataclass_fields_advanced(self):
        args = map_dataclass_fields(DataClass)
        self.assertEqual(args[0].name, "x")
        self.assertEqual(args[1].default, "abc")
        self.assertEqual(args[2].extras[0], "meta")

    def test_model_fields_extras(self):
        args = map_model_fields(ModelClass)
        for vti in args:
            self.assertIsInstance(vti, VarTypeInfo)

    def test_map_dataclass_fields_with_dict(self):
        args = map_dataclass_fields(DataClassWithDict)
        self.assertEqual(len(args), 1)
        self.assertEqual(args[0].name, "data")
        self.assert_dict_like(args[0])
        self.assertEqual(args[0].default, Dict)  # default_factory output

    def test_map_init_field_with_dict(self):
        args = map_init_field(InitClassWithDict)
        self.assertEqual(len(args), 1)
        self.assertEqual(args[0].name, "data")
        self.assert_dict_like(args[0])
        self.assertEqual(args[0].default, {})  # default value

    def test_map_model_fields_with_dict(self):
        args = map_model_fields(ModelClassWithDict)
        self.assertEqual(len(args), 1)
        self.assertEqual(args[0].name, "data")
        self.assert_dict_like(args[0])
        self.assertEqual(args[0].default, {})  # set as class-level value


if __name__ == "__main__":
    unittest.main()
