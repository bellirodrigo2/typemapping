import sys
from typing import Dict as Dict_t
from typing import List as List_t

from typing_extensions import Annotated, Any, Dict, List, Optional, Type

from typemapping import VarTypeInfo

TEST_TYPE = sys.version_info >= (3, 9)


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
