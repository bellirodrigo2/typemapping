# test_helpers.py

from typing import Annotated, Any, Callable, Mapping, Optional, Union


def func_mt() -> None:
    pass


def func_simple(arg1: str, arg2: int) -> None:
    pass


def func_def(arg1: str = "foobar", arg2: int = 12, arg3=True, arg4=None) -> None:  # type: ignore
    pass


def func_ann(
    arg1: Annotated[str, "meta1"],
    arg2: Annotated[int, "meta1", 2],
    arg3: Annotated[list[str], "meta1", 2, True],
    arg4: Annotated[dict[str, Any], "meta1", 2, True] = {"foo": "bar"},
) -> None:
    pass


def func_mix(arg1, arg2: Annotated[str, "meta1"], arg3: str, arg4="foobar") -> None:  # type: ignore
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
    arg_dep: str = ...,  # Ajuste conforme necessidade
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
