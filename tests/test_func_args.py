import unittest
from typing import Annotated, Optional, Union

from tests.test_helpers import MyClass, funcsmap
from typemapping import NO_DEFAULT, VarTypeInfo, get_field_type, get_func_args


class TestVarTypeInfos(unittest.TestCase):
    def setUp(self) -> None:
        self.funcsmap = funcsmap

    def test_istype_invalid_basetype(self) -> None:
        arg = VarTypeInfo("x", argtype=None, basetype="notatype", default=None)
        self.assertFalse(arg.istype(int))

    def test_funcarg_mt(self) -> None:
        mt = get_func_args(self.funcsmap["mt"])
        self.assertEqual(mt, [])

    def test_funcarg_simple(self) -> None:
        simple = get_func_args(self.funcsmap["simple"])
        self.assertEqual(len(simple), 2)
        self.assertEqual(simple[0].name, "arg1")
        self.assertIs(simple[0].argtype, str)
        self.assertIs(simple[0].basetype, str)
        self.assertEqual(simple[0].default, NO_DEFAULT)
        self.assertIsNone(simple[0].extras)
        self.assertTrue(simple[0].istype(str))
        self.assertFalse(simple[0].istype(int))

        self.assertEqual(simple[1].name, "arg2")
        self.assertIs(simple[1].argtype, int)
        self.assertIs(simple[1].basetype, int)
        self.assertEqual(simple[1].default, NO_DEFAULT)
        self.assertIsNone(simple[1].extras)
        self.assertTrue(simple[1].istype(int))
        self.assertFalse(simple[1].istype(str))

    def test_funcarg_def(self) -> None:
        def_ = get_func_args(self.funcsmap["def"])
        self.assertEqual(len(def_), 4)
        self.assertEqual(def_[0].default, "foobar")
        self.assertTrue(def_[2].istype(bool))

    def test_funcarg_ann(self) -> None:
        ann = get_func_args(self.funcsmap["ann"])
        self.assertEqual(len(ann), 4)

        self.assertEqual(ann[0].name, "arg1")
        self.assertEqual(ann[0].argtype, Annotated[str, "meta1"])
        self.assertIs(ann[0].basetype, str)
        self.assertEqual(ann[0].extras, ("meta1",))
        self.assertTrue(ann[0].hasinstance(str))
        self.assertEqual(ann[0].getinstance(str), "meta1")

    def test_funcarg_mix(self) -> None:
        mix = get_func_args(self.funcsmap["mix"])
        self.assertEqual(len(mix), 4)
        self.assertFalse(mix[0].istype(str))
        self.assertIsNone(mix[0].getinstance(str))

    def test_annotated_none(self) -> None:
        args = get_func_args(self.funcsmap["annotated_none"])
        self.assertEqual(len(args), 2)
        self.assertEqual(args[0].basetype, Optional[str])
        self.assertEqual(args[0].extras, ("meta",))
        self.assertFalse(args[1].hasinstance(int))

    def test_union(self) -> None:
        args = get_func_args(self.funcsmap["union"])
        self.assertEqual(len(args), 3)
        self.assertEqual(args[0].argtype, Union[int, str])
        self.assertEqual(args[1].basetype, Optional[float])

    def test_varargs(self) -> None:
        args = get_func_args(self.funcsmap["varargs"])
        self.assertEqual(len(args), 0)

    def test_kwonly(self) -> None:
        args = get_func_args(self.funcsmap["kwonly"])
        self.assertEqual(len(args), 2)
        self.assertEqual(args[1].default, "default")

    def test_forward(self) -> None:
        args = get_func_args(self.funcsmap["forward"])
        self.assertEqual(len(args), 1)
        self.assertIs(args[0].basetype, MyClass)

    def test_none_default(self) -> None:
        args = get_func_args(self.funcsmap["none_default"])
        self.assertEqual(len(args), 1)
        self.assertEqual(args[0].name, "arg")
        self.assertIsNone(args[0].default)
        self.assertEqual(args[0].basetype, Optional[str])

    def test_arg_without_type_or_default(self) -> None:
        def func(x):
            return x

        args = get_func_args(func)
        self.assertIsNone(args[0].argtype)
        self.assertEqual(args[0].default, NO_DEFAULT)

    def test_default_ellipsis(self) -> None:
        def func(x: str = ...) -> str:
            return x

        args = get_func_args(func)
        self.assertIs(args[0].default, Ellipsis)

    def test_star_args_handling(self) -> None:
        def func(a: str, *args, **kwargs):
            return a

        args = get_func_args(func)
        self.assertEqual(len(args), 1)

    def test_forward_ref_resolved(self) -> None:
        class NotDefinedType:
            pass

        def f(x: "NotDefinedType") -> None: ...

        args = get_func_args(func=f, localns=locals())
        self.assertIs(args[0].basetype, NotDefinedType)

    def test_class_field_x(self) -> None:
        class Model:
            x: int

        x = get_field_type(Model, "x")
        self.assertEqual(x, int)

    def test_class_field(self) -> None:
        class Model:
            x: int

            def __init__(self, y: str) -> None:
                self.y = y

            @property
            def w(self) -> bool:
                return True

            def z(self) -> int:
                return 42

        x = get_field_type(Model, "x")
        y = get_field_type(Model, "y")
        w = get_field_type(Model, "w")
        z = get_field_type(Model, "z")
        self.assertEqual(x, int)
        self.assertEqual(y, str)
        self.assertEqual(w, bool)
        self.assertEqual(z, int)

    def test_class_field_y(self) -> None:
        class Model:

            def __init__(self, y: str) -> None:
                self.y = y

        y = get_field_type(Model, "y")
        self.assertEqual(y, str)

    def test_class_field_w(self) -> None:
        class Model:
            @property
            def w(self) -> bool:
                return True

        w = get_field_type(Model, "w")
        self.assertEqual(w, bool)

    def test_class_field_z(self) -> None:
        class Model:
            def z(self) -> int:
                return 42

        z = get_field_type(Model, "z")
        self.assertEqual(z, int)

    def test_class_field_annotated(self) -> None:
        class Model:
            x: Annotated[int, "argx"]

            def __init__(self, y: Annotated[str, "argy"]) -> None:
                self.y = y

            @property
            def w(self) -> Annotated[bool, "argw"]:
                return True

            def z(self) -> Annotated[int, "argz"]:
                return 42

        x = get_field_type(Model, "x")
        y = get_field_type(Model, "y")
        w = get_field_type(Model, "w")
        z = get_field_type(Model, "z")

        self.assertEqual(x, int)
        self.assertEqual(y, str)
        self.assertEqual(w, bool)
        self.assertEqual(z, int)


if __name__ == "__main__":
    unittest.main()
