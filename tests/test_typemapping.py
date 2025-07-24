import sys
from dataclasses import dataclass, field
from typing import Dict as Dict_t
from typing import List as List_t

from typing_extensions import (Annotated, Any, Callable, Dict, List, Mapping,
                               Optional, Type, Union)

from typemapping import (NO_DEFAULT, VarTypeInfo, get_field_type,
                         get_func_args, map_dataclass_fields, map_init_field,
                         map_model_fields)

TEST_TYPE = sys.version_info >= (3, 9)

# ------------ ARGINFO---------------------


class MyBase: ...


class MySubBase(MyBase): ...


def make_vartypeinfo(
    basetype: Type[Any],
    name: str = "arg",
    argtype: Optional[Type[Any]] = None,
    default: Optional[Any] = None,
    has_default: bool = False,
    extras: Optional[tuple[Any, ...]] = None,
) -> VarTypeInfo:
    return VarTypeInfo(
        name=name,
        basetype=basetype,
        argtype=argtype or basetype,
        default=default,
        has_default=has_default,
        extras=extras,
    )


def test_basic() -> None:
    arg = make_vartypeinfo(basetype=MySubBase)
    assert not arg.istype(str)
    assert arg.istype(MyBase)


def test_list() -> None:
    arg = make_vartypeinfo(basetype=List[str])
    assert arg.istype(List[str])
    assert arg.istype(List_t[str])
    if TEST_TYPE:
        assert arg.istype(list[str])
    assert arg.istype(Annotated[List_t[str], "foobar"])
    assert not arg.istype(List[int])


def test_dict() -> None:
    arg = make_vartypeinfo(basetype=Dict[str, int])
    assert arg.istype(Dict[str, int])
    assert arg.istype(Dict_t[str, int])
    if TEST_TYPE:
        assert arg.istype(dict[str, int])
    assert arg.istype(Annotated[Dict[str, int], "foobar"])


# ------------ Class Args---------------------


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


# ------------ Func Args---------------------


def func_mt() -> None:
    pass


def func_simple(arg1: str, arg2: int) -> None:
    pass


def func_def(arg1: str = "foobar", arg2: int = 12, arg3=True, arg4=None) -> None:
    pass


def func_ann(
    arg1: Annotated[str, "meta1"],
    arg2: Annotated[int, "meta1", 2],
    arg3: Annotated[list[str], "meta1", 2, True],
    arg4: Annotated[dict[str, Any], "meta1", 2, True] = {"foo": "bar"},
) -> None:
    pass


def func_mix(arg1, arg2: Annotated[str, "meta1"], arg3: str, arg4="foobar") -> None:
    pass


def func_annotated_none(
    arg1: Annotated[Optional[str], "meta"],
    arg2: Annotated[Optional[int], "meta2"] = None,
) -> None:
    pass


def func_union(
    arg1: Union[int, str],
    arg2: Optional[float] = None,
    arg3: Annotated[Union[int, str], 1] = 2,
) -> None:
    pass


def func_varargs(*args: int, **kwargs: str) -> None:
    pass


def func_kwonly(*, arg1: int, arg2: str = "default") -> None:
    pass


def func_forward(arg: "MyClass") -> None:
    pass


class MyClass:
    pass


def func_none_default(arg: Optional[str] = None) -> None:
    pass


def inj_func(
    arg: str,
    arg_ann: Annotated[str, ...],
    arg_dep: str = ...,
):
    pass


funcsmap: Mapping[str, Callable[..., Any]] = {
    "mt": func_mt,
    "simple": func_simple,
    "def": func_def,
    "ann": func_ann,
    "mix": func_mix,
    "annotated_none": func_annotated_none,
    "union": func_union,
    "varargs": func_varargs,
    "kwonly": func_kwonly,
    "forward": func_forward,
    "none_default": func_none_default,
}


def test_istype_invalid_basetype() -> None:
    arg = VarTypeInfo("x", argtype=None, basetype="notatype", default=None)
    assert not arg.istype(int)


def test_funcarg_mt() -> None:
    mt = get_func_args(funcsmap["mt"])
    assert mt == []


def test_funcarg_simple() -> None:
    simple = get_func_args(funcsmap["simple"])
    assert len(simple) == 2
    assert simple[0].name == "arg1"
    assert simple[0].argtype is str
    assert simple[0].basetype is str
    assert simple[0].default == NO_DEFAULT
    assert simple[0].extras is None
    assert simple[0].istype(str)
    assert not simple[0].istype(int)

    assert simple[1].name == "arg2"
    assert simple[1].argtype is int
    assert simple[1].basetype is int
    assert simple[1].default == NO_DEFAULT
    assert simple[1].extras is None
    assert simple[1].istype(int)
    assert not simple[1].istype(str)


def test_funcarg_def() -> None:
    def_ = get_func_args(funcsmap["def"])
    assert len(def_) == 4
    assert def_[0].default == "foobar"
    assert def_[2].istype(bool)


def test_funcarg_ann() -> None:
    ann = get_func_args(funcsmap["ann"])
    assert len(ann) == 4

    assert ann[0].name == "arg1"
    assert ann[0].argtype == Annotated[str, "meta1"]
    assert ann[0].basetype is str
    assert ann[0].extras == ("meta1",)
    assert ann[0].hasinstance(str)
    assert ann[0].getinstance(str) == "meta1"


def test_funcarg_mix() -> None:
    mix = get_func_args(funcsmap["mix"])
    assert len(mix) == 4
    assert not mix[0].istype(str)
    assert mix[0].getinstance(str) is None


def test_annotated_none() -> None:
    args = get_func_args(funcsmap["annotated_none"])
    assert len(args) == 2
    assert args[0].basetype == Optional[str]
    assert args[0].extras == ("meta",)
    assert not args[1].hasinstance(int)


def test_union() -> None:
    args = get_func_args(funcsmap["union"])
    assert len(args) == 3
    assert args[0].argtype == Union[int, str]
    assert args[1].basetype == Optional[float]


def test_varargs() -> None:
    args = get_func_args(funcsmap["varargs"])
    assert len(args) == 0


def test_kwonly() -> None:
    args = get_func_args(funcsmap["kwonly"])
    assert len(args) == 2
    assert args[1].default == "default"


def test_forward() -> None:
    args = get_func_args(funcsmap["forward"])
    assert len(args) == 1
    assert args[0].basetype is MyClass


def test_none_default() -> None:
    args = get_func_args(funcsmap["none_default"])
    assert len(args) == 1
    assert args[0].name == "arg"
    assert args[0].default is None
    assert args[0].basetype == Optional[str]


def test_arg_without_type_or_default() -> None:
    def func(x):
        return x

    args = get_func_args(func)
    assert args[0].argtype is None
    assert args[0].default == NO_DEFAULT


def test_default_ellipsis() -> None:
    def func(x: str = ...) -> str:
        return x

    args = get_func_args(func)
    assert args[0].default is Ellipsis


def test_star_args_handling() -> None:
    def func(a: str, *args, **kwargs):
        return a

    args = get_func_args(func)
    assert len(args) == 1


def test_forward_ref_resolved() -> None:
    class NotDefinedType:
        pass

    def f(x: "NotDefinedType") -> None: ...

    args = get_func_args(func=f, localns=locals())
    assert args[0].basetype is NotDefinedType


def test_class_field_x() -> None:
    class Model:
        x: int

    assert get_field_type(Model, "x") is int


def test_class_field() -> None:
    class Model:
        x: int

        def __init__(self, y: str):
            self.y = y

        @property
        def w(self) -> bool:
            return True

        def z(self) -> int:
            return 42

    assert get_field_type(Model, "x") is int
    assert get_field_type(Model, "y") is str
    assert get_field_type(Model, "w") is bool
    assert get_field_type(Model, "z") is int


def test_class_field_y() -> None:
    class Model:
        def __init__(self, y: str):
            self.y = y

    assert get_field_type(Model, "y") is str


def test_class_field_w() -> None:
    class Model:
        @property
        def w(self) -> bool:
            return True

    assert get_field_type(Model, "w") is bool


def test_class_field_z() -> None:
    class Model:
        def z(self) -> int:
            return 42

    assert get_field_type(Model, "z") is int


def test_class_field_annotated() -> None:
    class Model:
        x: Annotated[int, "argx"]

        def __init__(self, y: Annotated[str, "argy"]):
            self.y = y

        @property
        def w(self) -> Annotated[bool, "argw"]:
            return True

        def z(self) -> Annotated[int, "argz"]:
            return 42

    assert get_field_type(Model, "x") is int
    assert get_field_type(Model, "y") is str
    assert get_field_type(Model, "w") is bool
    assert get_field_type(Model, "z") is int
