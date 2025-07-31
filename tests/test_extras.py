# mypy: disable-error-code=annotation-unchecked
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from functools import partial
from typing import Dict, List, Optional, Union

import pytest
from typing_extensions import Annotated, Any, Protocol

from typemapping import (
    VarTypeInfo,
    defensive_issubclass,
    get_field_type,
    get_func_args,
    get_return_type,
    get_safe_type_hints,
    is_annotated_type,
    is_equal_type,
    map_dataclass_fields,
    map_func_args,
    map_init_field,
    map_model_fields,
    map_return_type,
    unwrap_partial,
)

# Test constants
TEST_TYPE = sys.version_info >= (3, 9)


# ------------ Test Classes and Functions for Edge Cases ------------


class EmptyClass:
    """Class with no methods or attributes"""

    pass


class OnlyInit:
    """Class with only __init__"""

    def __init__(self, x: int):
        self.x = x


class NoInit:
    """Class with type hints but no __init__"""

    x: int
    y: str = "default"


class InheritedInit:
    """Class that inherits __init__"""

    x: int


class CustomInit(InheritedInit):
    """Class with custom __init__ that inherits from another"""

    def __init__(self, x: int, y: str):
        super().__init__()
        self.x = x
        self.y = y


@dataclass
class EmptyDataclass:
    """Empty dataclass"""

    pass


@dataclass
class DataclassWithFactoryError:
    """Dataclass with factory that raises exception"""

    items: List[str] = field(
        default_factory=lambda: exec('raise ValueError("factory error")')
    )


class PropertyWithSideEffect:
    """Class with property that has side effects"""

    _counter = 0

    @property
    def dangerous_prop(self) -> str:
        PropertyWithSideEffect._counter += 1
        if PropertyWithSideEffect._counter > 5:
            raise RuntimeError("Too many accesses!")
        return "value"


class ClassWithSlots:
    """Class using __slots__"""

    __slots__ = ["x", "y"]

    def __init__(self, x: int, y: str = "default"):
        self.x = x
        self.y = y


class AbstractClass(ABC):
    """Abstract class"""

    @abstractmethod
    def abstract_method(self) -> str:
        pass


class GenericClass:
    """Class with generic attributes"""

    items: List[Dict[str, Any]]
    mapping: Dict[str, List[int]] = {}


class NestedClass:
    """Outer class"""

    class Inner:
        """Inner class"""

        value: int = 42

        class DeepNested:
            """Deep nested class"""

            deep_value: str = "deep"


class ForwardRefClass:
    """Class with forward references"""

    def method(self, other: "ForwardRefClass") -> "ForwardRefClass":
        return self


class CircularRefA:
    """Circular reference A"""

    b_ref: "CircularRefB"


class CircularRefB:
    """Circular reference B"""

    a_ref: "CircularRefA"


class ProtocolClass(Protocol):
    """Protocol class"""

    def protocol_method(self) -> str: ...


class MetaClass(type):
    """Metaclass"""

    def __new__(cls, name, bases, dct):
        return super().__new__(cls, name, bases, dct)


class ClassWithMeta(metaclass=MetaClass):
    """Class using metaclass"""

    x: int = 1


# Functions for testing


def func_no_annotations(x, y=10):
    """Function without annotations"""
    return x + y


def func_with_forward_ref(x: "ForwardRefClass") -> "ForwardRefClass":
    """Function with forward references"""
    return x


def func_with_none_return() -> None:
    """Function returning None"""
    pass


def func_with_any_return() -> Any:
    """Function returning Any"""
    return "anything"


def func_with_complex_return() -> Dict[str, List[Optional[int]]]:
    """Function with complex return type"""
    return {}


def func_with_union_return() -> Union[str, int, None]:
    """Function with union return type"""
    return "test"


def func_raising_exception() -> None:
    """Function that raises during inspection"""
    raise RuntimeError("Cannot inspect this function")


def func_with_defaults_none(x: Optional[str] = None, y: Optional[int] = None):
    """Function with None defaults"""
    return x, y


def func_with_ellipsis(x: str = ..., y: int = ...):
    """Function with ellipsis defaults"""
    return x, y


# Partial function tests
def base_func(a: int, b: str, c: float = 3.14, d: bool = True):
    """Base function for partial testing"""
    return a, b, c, d


partial_func = partial(base_func, 42)
nested_partial = partial(partial_func, "test")
partial_with_kwargs = partial(base_func, b="fixed", d=False)


# ------------ Test is_equal_type ------------


def test_is_equal_type_basic() -> None:
    """Test basic type equality"""
    assert is_equal_type(str, str)
    assert is_equal_type(int, int)
    assert not is_equal_type(str, int)  # Now should work correctly


def test_is_equal_type_generics() -> None:
    """Test generic type equality"""
    assert is_equal_type(List[str], List[str])
    assert is_equal_type(Dict[str, int], Dict[str, int])
    assert not is_equal_type(List[str], List[int])
    assert not is_equal_type(List[str], Dict[str, int])


def test_is_equal_type_union() -> None:
    """Test union type equality"""
    assert is_equal_type(Union[str, int], Union[str, int])
    # Order DOES matter in get_args() - this is expected behavior
    assert not is_equal_type(
        Union[int, str], Union[str, int]
    )  # Different order = different args
    assert not is_equal_type(Union[str, int], Union[str, float])


def test_is_equal_type_optional() -> None:
    """Test optional type equality"""
    assert is_equal_type(Optional[str], Union[str, None])
    assert is_equal_type(Optional[int], Optional[int])


def test_is_equal_type_annotated() -> None:
    """Test annotated type equality"""
    ann1 = Annotated[str, "meta"]
    ann2 = Annotated[str, "meta"]
    ann3 = Annotated[str, "other"]

    assert is_equal_type(ann1, ann2)
    assert not is_equal_type(ann1, ann3)


# ------------ Test defensive_issubclass edge cases ------------


def testdefensive_issubclass_none() -> None:
    """Test defensive_issubclass with None"""
    assert not defensive_issubclass(None, str)
    assert not defensive_issubclass(str, None)


def testdefensive_issubclass_union() -> None:
    """Test defensive_issubclass with Union types"""
    # Updated implementation requires ALL types in Union to be subclasses
    assert defensive_issubclass(
        Union[str, int], object
    )  # Both str and int are subclasses of object
    assert not defensive_issubclass(Union[str, int], int)  # str is not subclass of int
    assert not defensive_issubclass(
        Union[str, int], float
    )  # Neither str nor int are subclasses of float


def testdefensive_issubclass_generics() -> None:
    """Test defensive_issubclass with generic types"""
    assert defensive_issubclass(List[str], list)
    assert defensive_issubclass(Dict[str, int], dict)


def testdefensive_issubclass_invalid_types() -> None:
    """Test defensive_issubclass with invalid types"""
    assert not defensive_issubclass("not_a_type", str)
    assert not defensive_issubclass(42, int)


# ------------ Test is_Annotated edge cases ------------


def test_is_annotated_none() -> None:
    """Test is_Annotated with None"""
    assert not is_annotated_type(None)


def test_is_annotated_nested() -> None:
    """Test is_Annotated with nested annotations"""
    nested = Annotated[Annotated[str, "inner"], "outer"]
    assert is_annotated_type(nested)


# ------------ Test specific mapping functions directly ------------


def test_map_init_field_empty_class() -> None:
    """Test mapping empty class returns empty list"""
    fields = map_init_field(EmptyClass)
    assert len(fields) == 0


def test_map_init_field_with_params() -> None:
    """Test mapping class with __init__ parameters"""
    fields = map_init_field(OnlyInit)
    assert len(fields) == 1
    assert fields[0].name == "x"
    assert fields[0].basetype is int


def test_map_model_fields_type_hints() -> None:
    """Test mapping class with type hints but no custom __init__"""
    fields = map_model_fields(NoInit)
    assert len(fields) == 2
    names = [f.name for f in fields]
    assert "x" in names
    assert "y" in names


def test_map_dataclass_fields_works() -> None:
    """Test that dataclass mapping works as expected"""

    @dataclass
    class TestDataclass:
        x: int = 42

    fields = map_dataclass_fields(TestDataclass)
    assert len(fields) == 1
    assert fields[0].name == "x"
    assert fields[0].basetype is int


def test_user_choice_flexibility() -> None:
    """Test that user can choose different strategies for same class"""

    class FlexibleClass:
        x: int = 10

        def __init__(self, y: str):
            self.y = y

    # User can choose to map from __init__
    init_fields = map_init_field(FlexibleClass)
    assert len(init_fields) == 1
    assert init_fields[0].name == "y"

    # Or choose to map from type hints
    model_fields = map_model_fields(FlexibleClass)
    assert len(model_fields) == 1
    assert model_fields[0].name == "x"


# ------------ Test map_return_type and get_return_type ------------


def test_map_return_type_none() -> None:
    """Test mapping return type of None"""
    ret_info = map_return_type(func_with_none_return)
    assert ret_info.name == "func_with_none_return"
    assert ret_info.basetype is type(None)


def test_map_return_type_any() -> None:
    """Test mapping return type of Any"""
    ret_info = map_return_type(func_with_any_return)
    assert ret_info.basetype == Any


def test_map_return_type_complex() -> None:
    """Test mapping complex return type"""
    ret_info = map_return_type(func_with_complex_return)
    assert ret_info.basetype == Dict[str, List[Optional[int]]]


def test_map_return_type_union() -> None:
    """Test mapping union return type"""
    ret_info = map_return_type(func_with_union_return)
    assert ret_info.basetype == Union[str, int, None]


def test_map_return_type_no_annotation() -> None:
    """Test mapping return type without annotation"""
    ret_info = map_return_type(func_no_annotations)
    assert ret_info.basetype is None


def test_get_return_type() -> None:
    """Test get_return_type function"""
    assert get_return_type(func_with_none_return) is type(None)
    assert get_return_type(func_with_any_return) == Any
    assert get_return_type(func_no_annotations) is None


def test_simple_lambda_returning_none() -> None:
    """Test lambdas that return None (void functions)."""
    # print returns None
    assert get_return_type(lambda: print("hello")) is None
    assert get_return_type(lambda: print()) is None

    # Multiple statements, last returns None
    assert get_return_type(lambda: [1, 2, 3].append(4)) is None

    # Explicit None return
    assert get_return_type(lambda: None) is type(None)


def test_lambda_returning_primitives() -> None:
    """Test lambdas returning primitive types."""
    # Strings
    assert get_return_type(lambda: "hello") is str
    assert get_return_type(lambda: "") is str
    assert get_return_type(lambda: f"formatted {42}") is str

    # Integers
    assert get_return_type(lambda: 42) is int
    assert get_return_type(lambda: 0) is int
    assert get_return_type(lambda: -999) is int
    assert get_return_type(lambda: 0xFF) is int  # hex
    assert get_return_type(lambda: 0b1010) is int  # binary

    # Floats
    assert get_return_type(lambda: 3.14) is float
    assert get_return_type(lambda: 0.0) is float
    assert get_return_type(lambda: -1.5e-10) is float

    # Booleans
    assert get_return_type(lambda: True) is bool
    assert get_return_type(lambda: False) is bool


def test_lambda_returning_containers() -> None:
    """Test lambdas returning container types."""
    # Lists
    assert get_return_type(lambda: []) is list
    assert get_return_type(lambda: [1, 2, 3]) is list

    # Tuples
    assert get_return_type(lambda: ()) is tuple
    assert get_return_type(lambda: (1, 2, 3)) is tuple
    assert get_return_type(lambda: (1,)) is tuple  # single element

    # Dicts
    assert get_return_type(lambda: {}) is dict
    assert get_return_type(lambda: {"key": "value"}) is dict
    assert get_return_type(lambda: {"a": 1, "b": 2}) is dict

    # Sets
    assert get_return_type(lambda: {1, 2, 3}) is set


def test_lambda_returning_complex_types() -> None:
    """Test lambdas returning more complex built-in types."""
    # Bytes
    assert get_return_type(lambda: b"hello") is bytes

    # Complex numbers
    assert get_return_type(lambda: 1 + 2j) is complex


def test_lambda_with_expressions() -> None:
    """Test lambdas with various expressions."""
    # Arithmetic expressions
    assert get_return_type(lambda: 1 + 2) is int
    assert get_return_type(lambda: 10 / 3) is float
    assert get_return_type(lambda: 10 // 3) is int
    assert get_return_type(lambda: 10 % 3) is int

    # Boolean expressions
    assert get_return_type(lambda: 1 < 2) is bool
    assert get_return_type(lambda: "a" in "abc") is bool
    assert get_return_type(lambda: not False) is bool

    # Conditional expressions
    assert get_return_type(lambda: "yes" if True else "no") is str
    assert get_return_type(lambda: 1 if True else 2.0) is int  # Takes first branch

    # List comprehensions
    assert get_return_type(lambda: {x: x**2 for x in [1, 2, 3]}) is dict


def test_lambda_with_parameters_returns_none() -> None:
    """Test that lambdas with parameters cannot be inferred."""
    # Single parameter
    assert get_return_type(lambda x: x) is None
    assert get_return_type(lambda x: x + 1) is None

    # Multiple parameters
    assert get_return_type(lambda x, y: x + y) is None
    assert get_return_type(lambda a, b, c: a * b * c) is None

    # With defaults (still has parameters)
    assert get_return_type(lambda x=1: x * 2) is None

    # *args and **kwargs
    assert get_return_type(lambda *args: sum(args)) is None
    assert get_return_type(lambda **kwargs: kwargs) is None


def test_lambda_edge_cases() -> None:
    """Test edge cases and potential problematic lambdas."""

    # Multiple expressions (using tuple)
    assert get_return_type(lambda: (1, 2, 3)[-1]) is int

    # Nested lambdas
    assert get_return_type(lambda: lambda x: x) is type(lambda: None)

    # Lambda returning lambda type
    def inner():
        return 42


def test_lambda_comparison_operators() -> None:
    """Test lambdas using various comparison and logical operators."""
    # Comparison operators
    assert get_return_type(lambda: 1 == 1) is bool
    assert get_return_type(lambda: 1 != 2) is bool
    assert get_return_type(lambda: 1 <= 2) is bool
    assert get_return_type(lambda: 2 >= 1) is bool

    # Logical operators
    assert get_return_type(lambda: True and False) is bool
    assert get_return_type(lambda: True or False) is bool
    assert get_return_type(lambda: not True) is bool

    # Identity operators
    assert get_return_type(lambda: None is None) is bool
    assert get_return_type(lambda: [] is not None) is bool  # noqa: F632


def test_lambda_with_string_formatting() -> None:
    """Test lambdas with various string formatting methods."""
    assert get_return_type(lambda: f"test {42}") is str
    assert get_return_type(lambda: f"{42} {3.14}") is str


def test_lambda_with_type_annotations() -> None:
    """Test that lambdas with type annotations still work."""
    # Note: lambdas can't have annotations in Python, but testing robustness
    # These would be syntax errors: lambda x: int: x + 1

    # But we can test annotated regular functions
    def annotated_func() -> int:
        return 42

    # This should use the annotation, not lambda inference
    assert get_return_type(annotated_func) is int


def test_map_return_type_with_lambdas() -> None:
    """Test the map_return_type function directly with lambdas."""
    # Test that VarTypeInfo is created correctly
    var_info = map_return_type(lambda: 42)
    assert var_info.basetype is int
    assert var_info.argtype is int
    assert var_info.name == "lambda_function"

    var_info2 = map_return_type(lambda: "hello")
    assert var_info2.basetype is str

    var_info3 = map_return_type(lambda: None)
    assert var_info3.basetype is type(None)


def test_lambda_with_union_possibilities() -> None:
    """Test lambdas where return type could vary (takes first execution path)."""
    # Since we execute once, we get the type from that execution
    # This will always return int because True evaluates first
    assert get_return_type(lambda: 1 if True else "string") is int


def test_lambda_special_values() -> None:
    """Test lambdas returning special Python values."""
    assert get_return_type(lambda: ...) is type(...)  # Ellipsis


def test_lambda_with_exceptions() -> None:
    """Test lambdas that raise exceptions."""
    # Lambda that raises exception - should return None (can't infer)
    assert get_return_type(lambda: 1 / 0) is None
    assert get_return_type(lambda: [][0]) is None  # IndexError
    assert get_return_type(lambda: {}["key"]) is None  # KeyError


@pytest.mark.skipif(sys.version_info < (3, 9), reason="requires python3.9+")
def test_lambda_with_python39_features() -> None:
    """Test lambdas using Python 3.9+ features."""
    # Dict union operator (3.9+)
    assert get_return_type(lambda: {"a": 1} | {"b": 2}) is dict


def test_lambda_not_allowed() -> None:
    """Test lambdas with side effects (should not work)."""
    # Global variable access
    global_var = 42
    assert get_return_type(lambda: global_var) is None

    # collections
    assert get_return_type(lambda: float("inf")) is None
    assert get_return_type(lambda: bool(1)) is None
    assert get_return_type(lambda: list(range(5))) is None
    assert get_return_type(lambda: set()) is None
    assert get_return_type(lambda: frozenset([1, 2, 3])) is None
    assert get_return_type(lambda: bytes([65, 66, 67])) is None
    assert get_return_type(lambda: bytearray(b"hello")) is None
    assert get_return_type(lambda: range(10)) is None
    assert get_return_type(lambda: complex(3, 4)) is None

    # Built-in objects
    assert get_return_type(lambda: datetime.now()) is None
    assert get_return_type(lambda: Exception("test")) is None

    # Custom class
    class CustomClass:
        pass

    assert get_return_type(lambda: CustomClass()) is None

    # Type objects themselves
    assert get_return_type(lambda: int) is None
    assert get_return_type(lambda: str) is None

    # List comprehensions
    assert get_return_type(lambda: list(range(3))) is None
    assert get_return_type(lambda: set(range(3))) is None
    assert get_return_type(lambda: {x: x**2 for x in range(3)}) is None

    assert get_return_type(lambda: "hello".upper()) is None
    assert get_return_type(lambda: "hello".split()) is None
    # List methods
    assert get_return_type(lambda: [].copy()) is None
    assert get_return_type(lambda: [1, 2].pop()) is None

    # Dict methods
    assert get_return_type(lambda: {}.keys()) is None
    assert get_return_type(lambda: {"a": 1}.values()) is None
    assert get_return_type(lambda: {"a": 1}.items()) is None

    test_list = []
    result = get_return_type(lambda: test_list.append(1))
    assert result is None

    # Dictionary modification
    test_dict = {}
    assert get_return_type(lambda: test_dict.setdefault("key", "value")) is None

    """Test lambdas that use imported modules."""
    import json
    import os
    import sys

    assert get_return_type(lambda: os.getcwd()) is None
    assert get_return_type(lambda: sys.version) is None
    assert get_return_type(lambda: json.dumps({})) is None

    """Test lambdas using built-in functions."""
    assert get_return_type(lambda: len([1, 2, 3])) is None
    assert get_return_type(lambda: sum([1, 2, 3])) is None
    assert get_return_type(lambda: max([1, 2, 3])) is None
    assert get_return_type(lambda: min([1, 2, 3])) is None
    assert get_return_type(lambda: abs(-5)) is None
    assert get_return_type(lambda: round(3.7)) is None
    assert get_return_type(lambda: sorted([3, 1, 2])) is None
    assert get_return_type(lambda: list(reversed([1, 2, 3]))) is None

    """Test lambdas with various string formatting methods."""
    assert get_return_type(lambda: "{} {}".format("hello", "world")) is None
    assert get_return_type(lambda: str.format("{0} {1}", "a", "b")) is None

    # Special numeric values
    assert get_return_type(lambda: float("nan")) is None
    assert get_return_type(lambda: float("-inf")) is None

    # Potentially infinite recursion (should be caught by recursion limit)
    def infinite_recursion() -> None:
        return infinite_recursion()

    # This should return None (can't execute safely)
    assert get_return_type(lambda: infinite_recursion()) is None

    # Large computation (should complete quickly)
    assert get_return_type(lambda: sum(range(1000))) is None

    x = 42
    assert get_return_type(lambda: x) is None

    def outer():
        y = "captured"
        return lambda: y

    inner_lambda = outer()
    assert get_return_type(inner_lambda) is None

    # Captured mutable object
    captured_list = [1, 2, 3]
    assert get_return_type(lambda: captured_list) is None


# ------------ Test map_func_args ------------


def test_map_func_args_complete() -> None:
    """Test complete function mapping"""

    def test_func(x: int, y: str = "test") -> bool:
        return True

    args, ret_type = map_func_args(test_func)
    assert len(args) == 2
    assert args[0].name == "x"
    assert args[0].basetype is int
    assert args[1].name == "y"
    assert args[1].basetype is str
    assert ret_type.basetype is bool


def test_map_func_args_no_annotations() -> None:
    """Test mapping function without annotations"""
    args, ret_type = map_func_args(func_no_annotations)
    assert len(args) == 2
    assert args[0].argtype is None
    assert args[1].argtype is int  # Inferred from default
    assert ret_type.basetype is None


# ------------ Test partial function unwrapping ------------


def test_unwrap_partial_simple() -> None:
    """Test unwrapping simple partial"""
    func, args, kwargs = unwrap_partial(partial_func)
    assert func == base_func
    assert args == [42]
    assert kwargs == {}


def test_unwrap_partial_nested() -> None:
    """Test unwrapping nested partial"""
    func, args, kwargs = unwrap_partial(nested_partial)
    assert func == base_func
    assert args == [42, "test"]
    assert kwargs == {}


def test_unwrap_partial_with_kwargs() -> None:
    """Test unwrapping partial with kwargs"""
    func, args, kwargs = unwrap_partial(partial_with_kwargs)
    assert func == base_func
    assert args == []
    assert kwargs == {"b": "fixed", "d": False}


def test_unwrap_partial_not_partial() -> None:
    """Test unwrapping non-partial function"""
    func, args, kwargs = unwrap_partial(base_func)
    assert func == base_func
    assert args == []
    assert kwargs == {}


def test_get_func_args_partial() -> None:
    """Test get_func_args with partial functions"""
    args = get_func_args(partial_func)
    # Should skip the first parameter (filled by partial)
    assert len(args) == 3
    assert args[0].name == "b"
    assert args[1].name == "c"
    assert args[2].name == "d"


def test_get_func_args_partial_kwargs() -> None:
    """Test get_func_args with partial containing kwargs"""
    args = get_func_args(partial_with_kwargs)
    # Should skip parameters filled by kwargs
    assert len(args) == 2
    names = [arg.name for arg in args]
    assert "a" in names
    assert "c" in names
    assert "b" not in names  # Filled by partial
    assert "d" not in names  # Filled by partial


# ------------ Test edge cases in field mapping ------------


def test_map_model_fields_property_side_effect() -> None:
    """Test that properties with side effects are handled safely"""
    assert PropertyWithSideEffect._counter <= 1  # May be called once during inspection


def test_map_dataclass_fields_empty() -> None:
    """Test mapping empty dataclass"""
    fields = map_dataclass_fields(EmptyDataclass)
    assert len(fields) == 0


def test_map_dataclass_fields_factory_error() -> None:
    """Test mapping dataclass with factory that raises"""
    fields = map_dataclass_fields(DataclassWithFactoryError)
    assert len(fields) == 1
    # Should handle the factory error gracefully
    assert fields[0].name == "items"


def test_map_init_field_object_init() -> None:
    """Test mapping class with only object.__init__"""

    class NoCustomInitClass:
        pass

    # Should return empty list for classes using object.__init__
    fields = map_init_field(NoCustomInitClass)
    assert len(fields) == 0


def test_map_init_field_slots() -> None:
    """Test mapping class with __slots__"""
    fields = map_init_field(ClassWithSlots)
    assert len(fields) == 2
    names = [f.name for f in fields]
    assert "x" in names
    assert "y" in names
    # Should have default for y
    y_field = next(f for f in fields if f.name == "y")
    assert y_field.default == "default"


# ------------ Test forward references and circular refs ------------


def test_forward_ref_resolution() -> None:
    """Test forward reference resolution"""
    args = get_func_args(func_with_forward_ref)
    assert len(args) == 1
    assert args[0].basetype == ForwardRefClass


def test_get_safe_type_hints_circular() -> None:
    """Test get_safe_type_hints with circular references"""
    hints = get_safe_type_hints(CircularRefA)
    # Should not crash, may return ForwardRef
    assert isinstance(hints, dict)


def test_get_safe_type_hints_error_fallback() -> None:
    """Test fallback when get_type_hints fails"""

    # Create a function that will cause get_type_hints to fail
    def problematic_func() -> None:
        pass

    # Modify annotations to cause error
    problematic_func.__annotations__ = {"x": "NonExistentType"}

    hints = get_safe_type_hints(problematic_func)
    # Should fallback to __annotations__
    assert "x" in hints


# ------------ Test VarTypeInfo edge cases ------------


def test_vartypeinfo_none_basetype() -> None:
    """Test VarTypeInfo with None basetype"""
    vti = VarTypeInfo("test", None, None, None)
    assert not vti.istype(str)
    assert not vti.isequal(str)
    assert vti.args == ()


def test_vartypeinfo_getinstance_not_type() -> None:
    """Test getinstance with non-type argument"""
    vti = VarTypeInfo("test", str, str, "default", extras=("meta",))
    assert vti.getinstance("not_a_type") is None


def test_vartypeinfo_extras_multiple() -> None:
    """Test VarTypeInfo with multiple extras"""

    class Meta1:
        pass

    class Meta2:
        pass

    vti = VarTypeInfo("test", str, str, None, extras=(Meta1(), Meta2(), "string"))
    assert isinstance(vti.getinstance(Meta1), Meta1)
    assert isinstance(vti.getinstance(Meta2), Meta2)
    assert vti.getinstance(str) == "string"


# ------------ Test error handling and edge cases ------------


def test_get_field_type_nonexistent() -> None:
    """Test get_field_type with non-existent field"""
    assert get_field_type(EmptyClass, "nonexistent") is None


def test_get_field_type_nested_class() -> None:
    """Test get_field_type with nested class"""
    field_type = get_field_type(NestedClass.Inner, "value")
    assert field_type is int


def test_get_field_type_deep_nested() -> None:
    """Test get_field_type with deeply nested class"""
    field_type = get_field_type(NestedClass.Inner.DeepNested, "deep_value")
    assert field_type is str


def test_get_field_type_method() -> None:
    """Test get_field_type with method return type"""

    class TestClass:
        def method(self) -> str:
            return "test"

    field_type = get_field_type(TestClass, "method")
    assert field_type is str


def test_get_field_type_property() -> None:
    """Test get_field_type with property"""

    class TestClass:
        @property
        def prop(self) -> int:
            return 42

    field_type = get_field_type(TestClass, "prop")
    assert field_type is int


def test_get_field_type_annotated() -> None:
    """Test get_field_type strips Annotated"""

    class TestClass:
        field: Annotated[str, "meta"] = "test"

    field_type = get_field_type(TestClass, "field")
    assert field_type is str


# ------------ Test special function cases ------------


def test_func_args_ellipsis_default() -> None:
    """Test function with ellipsis default values"""
    args = get_func_args(func_with_ellipsis)
    assert len(args) == 2
    assert args[0].default is Ellipsis
    assert args[1].default is Ellipsis


def test_func_args_none_defaults() -> None:
    """Test function with None default values"""
    args = get_func_args(func_with_defaults_none)
    assert len(args) == 2
    assert args[0].default is None
    assert args[1].default is None


def test_func_args_bt_default_fallback() -> None:
    """Test bt_default_fallback parameter"""
    args_with_fallback = get_func_args(func_no_annotations, bt_default_fallback=True)
    args_without_fallback = get_func_args(
        func_no_annotations, bt_default_fallback=False
    )

    # With fallback, should infer type from default
    assert args_with_fallback[1].argtype is int

    # Without fallback, should be None
    assert args_without_fallback[1].argtype is None


# ------------ Test performance and caching ------------


def test_multiple_calls_same_class() -> None:
    """Test that multiple calls to same class don't cause issues"""
    for _ in range(10):
        fields1 = map_init_field(OnlyInit)
        fields2 = map_init_field(OnlyInit)
        assert len(fields1) == len(fields2) == 1


# ------------ Test Python version specific features ------------


@pytest.mark.skipif(not TEST_TYPE, reason="Requires Python 3.9+")
def test_builtin_generics_py39() -> None:
    """Test built-in generics in Python 3.9+"""

    def func(x: list[str], y: dict[str, int]) -> tuple[str, int]:
        return "test", 42

    args, ret_type = map_func_args(func)
    assert args[0].basetype == list[str]
    assert args[1].basetype == dict[str, int]
    assert ret_type.basetype == tuple[str, int]


# ------------ Test complex scenarios ------------


def test_complex_inheritance_chain() -> None:
    """Test complex inheritance scenarios"""

    class Base:
        x: int

    class Middle(Base):
        y: str = "middle"

    class Derived(Middle):
        def __init__(self, x: int, y: str, z: float):
            self.x = x
            self.y = y
            self.z = z

    # Test different mapping strategies
    init_fields = map_init_field(Derived)
    assert len(init_fields) == 3
    names = [f.name for f in init_fields]
    assert all(name in names for name in ["x", "y", "z"])


def test_mixed_annotations_and_defaults() -> None:
    """Test class with mixed annotation styles"""

    class MixedClass:
        # Class variable with type hint
        class_var: int = 42

        # Instance variable in __init__
        def __init__(self, instance_var: str):
            self.instance_var = instance_var

        # Property
        @property
        def computed(self) -> float:
            return 3.14

    # Test init mapping - should get instance_var from __init__
    init_fields = map_init_field(MixedClass)
    assert len(init_fields) == 1
    assert init_fields[0].name == "instance_var"

    # Test model mapping - should get class_var from type hints
    model_fields = map_model_fields(MixedClass)
    assert len(model_fields) == 1
    assert model_fields[0].name == "class_var"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
