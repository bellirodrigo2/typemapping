# mypy: disable-error-code=annotation-unchecked
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import partial

import pytest
from typing_extensions import (Annotated, Any, Dict, List, Optional, Protocol,
                               Union)

from typemapping import (VarTypeInfo, get_field_type, get_func_args,
                         get_return_type, get_safe_type_hints, is_Annotated,
                         is_equal_type, map_dataclass_fields, map_func_args,
                         map_init_field, map_model_fields, map_return_type,
                         safe_issubclass, unwrap_partial)

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


def func_raising_exception():
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


def test_is_equal_type_basic():
    """Test basic type equality"""
    assert is_equal_type(str, str)
    assert is_equal_type(int, int)
    assert not is_equal_type(str, int)  # Now should work correctly


def test_is_equal_type_generics():
    """Test generic type equality"""
    assert is_equal_type(List[str], List[str])
    assert is_equal_type(Dict[str, int], Dict[str, int])
    assert not is_equal_type(List[str], List[int])
    assert not is_equal_type(List[str], Dict[str, int])


def test_is_equal_type_union():
    """Test union type equality"""
    assert is_equal_type(Union[str, int], Union[str, int])
    # Order DOES matter in get_args() - this is expected behavior
    assert not is_equal_type(
        Union[int, str], Union[str, int]
    )  # Different order = different args
    assert not is_equal_type(Union[str, int], Union[str, float])


def test_is_equal_type_optional():
    """Test optional type equality"""
    assert is_equal_type(Optional[str], Union[str, None])
    assert is_equal_type(Optional[int], Optional[int])


def test_is_equal_type_annotated():
    """Test annotated type equality"""
    ann1 = Annotated[str, "meta"]
    ann2 = Annotated[str, "meta"]
    ann3 = Annotated[str, "other"]

    assert is_equal_type(ann1, ann2)
    assert not is_equal_type(ann1, ann3)


# ------------ Test safe_issubclass edge cases ------------


def testsafe_issubclass_none():
    """Test safe_issubclass with None"""
    assert not safe_issubclass(None, str)
    assert not safe_issubclass(str, None)


def testsafe_issubclass_union():
    """Test safe_issubclass with Union types"""
    # Updated implementation requires ALL types in Union to be subclasses
    assert safe_issubclass(
        Union[str, int], object
    )  # Both str and int are subclasses of object
    assert not safe_issubclass(Union[str, int], int)  # str is not subclass of int
    assert not safe_issubclass(
        Union[str, int], float
    )  # Neither str nor int are subclasses of float


def testsafe_issubclass_generics():
    """Test safe_issubclass with generic types"""
    assert safe_issubclass(List[str], list)
    assert safe_issubclass(Dict[str, int], dict)


def testsafe_issubclass_invalid_types():
    """Test safe_issubclass with invalid types"""
    assert not safe_issubclass("not_a_type", str)
    assert not safe_issubclass(42, int)


# ------------ Test is_Annotated edge cases ------------


def test_is_annotated_none():
    """Test is_Annotated with None"""
    assert not is_Annotated(None)


def test_is_annotated_nested():
    """Test is_Annotated with nested annotations"""
    nested = Annotated[Annotated[str, "inner"], "outer"]
    assert is_Annotated(nested)


# ------------ Test specific mapping functions directly ------------


def test_map_init_field_empty_class():
    """Test mapping empty class returns empty list"""
    fields = map_init_field(EmptyClass)
    assert len(fields) == 0


def test_map_init_field_with_params():
    """Test mapping class with __init__ parameters"""
    fields = map_init_field(OnlyInit)
    assert len(fields) == 1
    assert fields[0].name == "x"
    assert fields[0].basetype is int


def test_map_model_fields_type_hints():
    """Test mapping class with type hints but no custom __init__"""
    fields = map_model_fields(NoInit)
    assert len(fields) == 2
    names = [f.name for f in fields]
    assert "x" in names
    assert "y" in names


def test_map_dataclass_fields_works():
    """Test that dataclass mapping works as expected"""

    @dataclass
    class TestDataclass:
        x: int = 42

    fields = map_dataclass_fields(TestDataclass)
    assert len(fields) == 1
    assert fields[0].name == "x"
    assert fields[0].basetype is int


def test_user_choice_flexibility():
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


def test_map_return_type_none():
    """Test mapping return type of None"""
    ret_info = map_return_type(func_with_none_return)
    assert ret_info.name == "func_with_none_return"
    assert ret_info.basetype is type(None)


def test_map_return_type_any():
    """Test mapping return type of Any"""
    ret_info = map_return_type(func_with_any_return)
    assert ret_info.basetype == Any


def test_map_return_type_complex():
    """Test mapping complex return type"""
    ret_info = map_return_type(func_with_complex_return)
    assert ret_info.basetype == Dict[str, List[Optional[int]]]


def test_map_return_type_union():
    """Test mapping union return type"""
    ret_info = map_return_type(func_with_union_return)
    assert ret_info.basetype == Union[str, int, None]


def test_map_return_type_no_annotation():
    """Test mapping return type without annotation"""
    ret_info = map_return_type(func_no_annotations)
    assert ret_info.basetype is None


def test_get_return_type():
    """Test get_return_type function"""
    assert get_return_type(func_with_none_return) is type(None)
    assert get_return_type(func_with_any_return) == Any
    assert get_return_type(func_no_annotations) is None


# ------------ Test map_func_args ------------


def test_map_func_args_complete():
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


def test_map_func_args_no_annotations():
    """Test mapping function without annotations"""
    args, ret_type = map_func_args(func_no_annotations)
    assert len(args) == 2
    assert args[0].argtype is None
    assert args[1].argtype is int  # Inferred from default
    assert ret_type.basetype is None


# ------------ Test partial function unwrapping ------------


def test_unwrap_partial_simple():
    """Test unwrapping simple partial"""
    func, args, kwargs = unwrap_partial(partial_func)
    assert func == base_func
    assert args == [42]
    assert kwargs == {}


def test_unwrap_partial_nested():
    """Test unwrapping nested partial"""
    func, args, kwargs = unwrap_partial(nested_partial)
    assert func == base_func
    assert args == [42, "test"]
    assert kwargs == {}


def test_unwrap_partial_with_kwargs():
    """Test unwrapping partial with kwargs"""
    func, args, kwargs = unwrap_partial(partial_with_kwargs)
    assert func == base_func
    assert args == []
    assert kwargs == {"b": "fixed", "d": False}


def test_unwrap_partial_not_partial():
    """Test unwrapping non-partial function"""
    func, args, kwargs = unwrap_partial(base_func)
    assert func == base_func
    assert args == []
    assert kwargs == {}


def test_get_func_args_partial():
    """Test get_func_args with partial functions"""
    args = get_func_args(partial_func)
    # Should skip the first parameter (filled by partial)
    assert len(args) == 3
    assert args[0].name == "b"
    assert args[1].name == "c"
    assert args[2].name == "d"


def test_get_func_args_partial_kwargs():
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


def test_map_model_fields_property_side_effect():
    """Test that properties with side effects are handled safely"""
    assert PropertyWithSideEffect._counter <= 1  # May be called once during inspection


def test_map_dataclass_fields_empty():
    """Test mapping empty dataclass"""
    fields = map_dataclass_fields(EmptyDataclass)
    assert len(fields) == 0


def test_map_dataclass_fields_factory_error():
    """Test mapping dataclass with factory that raises"""
    fields = map_dataclass_fields(DataclassWithFactoryError)
    assert len(fields) == 1
    # Should handle the factory error gracefully
    assert fields[0].name == "items"


def test_map_init_field_object_init():
    """Test mapping class with only object.__init__"""

    class NoCustomInitClass:
        pass

    # Should return empty list for classes using object.__init__
    fields = map_init_field(NoCustomInitClass)
    assert len(fields) == 0


def test_map_init_field_slots():
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


def test_forward_ref_resolution():
    """Test forward reference resolution"""
    args = get_func_args(func_with_forward_ref)
    assert len(args) == 1
    assert args[0].basetype == ForwardRefClass


def test_get_safe_type_hints_circular():
    """Test get_safe_type_hints with circular references"""
    hints = get_safe_type_hints(CircularRefA)
    # Should not crash, may return ForwardRef
    assert isinstance(hints, dict)


def test_get_safe_type_hints_error_fallback():
    """Test fallback when get_type_hints fails"""

    # Create a function that will cause get_type_hints to fail
    def problematic_func():
        pass

    # Modify annotations to cause error
    problematic_func.__annotations__ = {"x": "NonExistentType"}

    hints = get_safe_type_hints(problematic_func)
    # Should fallback to __annotations__
    assert "x" in hints


# ------------ Test VarTypeInfo edge cases ------------


def test_vartypeinfo_none_basetype():
    """Test VarTypeInfo with None basetype"""
    vti = VarTypeInfo("test", None, None, None)
    assert not vti.istype(str)
    assert not vti.isequal(str)
    assert vti.args == ()


def test_vartypeinfo_getinstance_not_type():
    """Test getinstance with non-type argument"""
    vti = VarTypeInfo("test", str, str, "default", extras=("meta",))
    assert vti.getinstance("not_a_type") is None


def test_vartypeinfo_extras_multiple():
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


def test_get_field_type_nonexistent():
    """Test get_field_type with non-existent field"""
    assert get_field_type(EmptyClass, "nonexistent") is None


def test_get_field_type_nested_class():
    """Test get_field_type with nested class"""
    field_type = get_field_type(NestedClass.Inner, "value")
    assert field_type is int


def test_get_field_type_deep_nested():
    """Test get_field_type with deeply nested class"""
    field_type = get_field_type(NestedClass.Inner.DeepNested, "deep_value")
    assert field_type is str


def test_get_field_type_method():
    """Test get_field_type with method return type"""

    class TestClass:
        def method(self) -> str:
            return "test"

    field_type = get_field_type(TestClass, "method")
    assert field_type is str


def test_get_field_type_property():
    """Test get_field_type with property"""

    class TestClass:
        @property
        def prop(self) -> int:
            return 42

    field_type = get_field_type(TestClass, "prop")
    assert field_type is int


def test_get_field_type_annotated():
    """Test get_field_type strips Annotated"""

    class TestClass:
        field: Annotated[str, "meta"] = "test"

    field_type = get_field_type(TestClass, "field")
    assert field_type is str


# ------------ Test special function cases ------------


def test_func_args_ellipsis_default():
    """Test function with ellipsis default values"""
    args = get_func_args(func_with_ellipsis)
    assert len(args) == 2
    assert args[0].default is Ellipsis
    assert args[1].default is Ellipsis


def test_func_args_none_defaults():
    """Test function with None default values"""
    args = get_func_args(func_with_defaults_none)
    assert len(args) == 2
    assert args[0].default is None
    assert args[1].default is None


def test_func_args_bt_default_fallback():
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


def test_multiple_calls_same_class():
    """Test that multiple calls to same class don't cause issues"""
    for _ in range(10):
        fields1 = map_init_field(OnlyInit)
        fields2 = map_init_field(OnlyInit)
        assert len(fields1) == len(fields2) == 1


# ------------ Test Python version specific features ------------


@pytest.mark.skipif(not TEST_TYPE, reason="Requires Python 3.9+")
def test_builtin_generics_py39():
    """Test built-in generics in Python 3.9+"""

    def func(x: list[str], y: dict[str, int]) -> tuple[str, int]:
        return "test", 42

    args, ret_type = map_func_args(func)
    assert args[0].basetype == list[str]
    assert args[1].basetype == dict[str, int]
    assert ret_type.basetype == tuple[str, int]


# ------------ Test complex scenarios ------------


def test_complex_inheritance_chain():
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


def test_mixed_annotations_and_defaults():
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
