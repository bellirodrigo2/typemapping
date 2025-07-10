import sys
import unittest
from typing import Dict as Dict_t
from typing import List as List_t

from typing_extensions import Annotated, Any, Dict, List, Optional, Type

from typemapping.typemapping import VarTypeInfo

if sys.version_info >= (3, 9):
    TEST_TYPE = True
else:
    TEST_TYPE = False


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


class MyBase: ...


class MySubBase(MyBase): ...


class TestVarTypeInfo(unittest.TestCase):

    def test_basic(self) -> None:
        arg = make_vartypeinfo(basetype=MySubBase)
        self.assertFalse(arg.istype(str))
        self.assertTrue(arg.istype(MyBase))

    def test_list(self) -> None:
        arg = make_vartypeinfo(basetype=List[str])
        self.assertTrue(arg.istype(List[str]))
        self.assertTrue(arg.istype(List_t[str]))
        if TEST_TYPE:
            self.assertTrue(arg.istype(list[str]))

        self.assertTrue(arg.istype(Annotated[List_t[str], "foobar"]))
        self.assertFalse(arg.istype(List[int]))

    def test_dict(self) -> None:
        arg = make_vartypeinfo(basetype=Dict[str, int])
        self.assertTrue(arg.istype(Dict[str, int]))
        self.assertTrue(arg.istype(Dict_t[str, int]))
        if TEST_TYPE:
            self.assertTrue(arg.istype(dict[str, int]))

        self.assertTrue(arg.istype(Annotated[Dict[str, int], "foobar"]))
