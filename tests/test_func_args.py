from typing_extensions import Annotated, Any, Callable, Mapping, Optional, Union

from typemapping import NO_DEFAULT, VarTypeInfo, get_field_type, get_func_args

# Funções de teste


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
