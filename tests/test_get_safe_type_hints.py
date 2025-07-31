# Classes e funções de teste
import sys
from unittest.mock import patch

import pytest

from typemapping.typemapping import get_safe_type_hints


class SimpleClass:
    x: int
    y: str


class NestedClass:
    class Inner:
        z: "SimpleClass"


def simple_function(x: int, y: str) -> None:
    pass


def forward_ref_function(x: "SimpleClass") -> "SimpleClass":
    return x


class SelfReferencingClass:
    def method(self: "SelfReferencingClass") -> "SelfReferencingClass":  # noqa: F821
        return self


class InvalidTypeHintClass:
    x: "NonExistentType"  # noqa: F821


# Objeto sem atributos esperados
class BadObject:
    pass  # Will modify __dict__ in test


# Helper to normalize None types across Python versions
def normalize_none_type(hints):
    """Convert None to type(None) for consistent comparison across Python versions."""
    normalized = {}
    for key, value in hints.items():
        if value is None and key == "return":
            normalized[key] = type(None)
        elif value is None:
            # For non-return annotations, keep as is in 3.8 or convert in 3.9+
            if sys.version_info >= (3, 9):
                normalized[key] = type(None)
            else:
                normalized[key] = None
        else:
            normalized[key] = value
    return normalized


# Testes
def test_class_with_valid_type_hints() -> None:
    result = get_safe_type_hints(SimpleClass)
    assert result == {"x": int, "y": str}


def test_function_with_valid_type_hints() -> None:
    result = get_safe_type_hints(simple_function)
    expected = {"x": int, "y": str, "return": type(None)}
    assert normalize_none_type(result) == expected


def test_forward_ref_function() -> None:
    result = get_safe_type_hints(forward_ref_function)
    assert result == {"x": SimpleClass, "return": SimpleClass}


def test_self_referencing_class() -> None:
    result = get_safe_type_hints(SelfReferencingClass.method)
    assert result == {"self": SelfReferencingClass, "return": SelfReferencingClass}


def test_nested_class() -> None:
    result = get_safe_type_hints(NestedClass.Inner)
    assert result == {"z": SimpleClass}


def test_localns_provided() -> None:
    localns = {"CustomType": int}

    class FuncContainer:
        @staticmethod
        def func_with_custom_type(x: "CustomType") -> None:  # noqa: F821
            pass

    result = get_safe_type_hints(FuncContainer.func_with_custom_type, localns=localns)
    expected = {"x": int, "return": type(None)}
    assert normalize_none_type(result) == expected


def test_python_38_none_type() -> None:
    # This test needs to work differently in Python 3.8 vs 3.9+
    def func_with_none(x: None) -> None:
        pass

    result = get_safe_type_hints(func_with_none)

    if sys.version_info >= (3, 9):
        # Python 3.9+ converts None to type(None)
        assert result == {"x": type(None), "return": type(None)}
    else:
        # Python 3.8 behavior - get_type_hints might return None
        # The actual behavior depends on the implementation
        assert "x" in result
        assert "return" in result
        # Both could be None or type(None) depending on implementation


def test_attribute_error_on_invalid_object() -> None:
    # Create an object that will raise AttributeError when accessing __annotations__
    bad_obj = BadObject()

    # Make __annotations__ raise AttributeError
    def raise_attribute_error():
        raise AttributeError("No annotations")

    type(bad_obj).__annotations__ = property(lambda self: raise_attribute_error())

    result = get_safe_type_hints(bad_obj)
    assert result == {}

    # Clean up
    delattr(type(bad_obj), "__annotations__")


def test_attribute_error_on_missing_module() -> None:
    # Create a mock class with a non-existent module
    class NoModuleClass:
        x: int

    # Temporarily set a bad module
    original_module = NoModuleClass.__module__
    NoModuleClass.__module__ = "non_existent_module"

    try:
        result = get_safe_type_hints(NoModuleClass)
        # Should still get annotations from __annotations__
        assert result == {"x": int}
    finally:
        NoModuleClass.__module__ = original_module


def test_type_error_on_invalid_type_hint() -> None:
    result = get_safe_type_hints(InvalidTypeHintClass)
    # With unresolvable forward refs, should fallback to string
    assert result == {"x": "NonExistentType"}


def test_fallback_with_annotations() -> None:
    # Create a function with custom annotations
    def func_with_annotations() -> None:
        pass

    # Set annotations directly
    func_with_annotations.__annotations__ = {"x": "SimpleClass", "return": None}

    result = get_safe_type_hints(
        func_with_annotations, localns={"SimpleClass": SimpleClass}
    )

    # The function should try to resolve forward refs
    expected = {"x": SimpleClass, "return": type(None)}
    assert normalize_none_type(result) == expected


def test_fallback_without_annotations() -> None:
    class NoAnnotations:
        pass

    result = get_safe_type_hints(NoAnnotations)
    assert result == {}


def test_key_error_on_qualname_parts() -> None:
    def bad_qualname_func() -> None:
        pass

    # Save original values
    original_qualname = bad_qualname_func.__qualname__
    original_module = bad_qualname_func.__module__

    # Set bad values
    bad_qualname_func.__qualname__ = "Invalid.Module.Func"
    bad_qualname_func.__module__ = "non_existent_module"

    try:
        result = get_safe_type_hints(bad_qualname_func)
        # Should still get basic return annotation
        expected = {"return": type(None)}
        assert normalize_none_type(result) == expected
    finally:
        # Restore original values
        bad_qualname_func.__qualname__ = original_qualname
        bad_qualname_func.__module__ = original_module


def test_empty_globalns_and_localns() -> None:
    # Create a new function to avoid modifying the original
    code = compile("def func(): pass", "<string>", "exec")
    namespace = {}
    exec(code, namespace)
    func_without_globals = namespace["func"]

    # Function should have minimal globals
    result = get_safe_type_hints(func_without_globals)
    # Should return empty dict since no annotations
    assert result == {}


def test_recursion_error_handling() -> None:
    with patch("typing.get_type_hints", side_effect=RecursionError):
        result = get_safe_type_hints(SimpleClass)
        # Should fallback to __annotations__
        assert result == {"x": int, "y": str}


def test_none_localns() -> None:
    result = get_safe_type_hints(simple_function, localns=None)
    expected = {"x": int, "y": str, "return": type(None)}
    assert normalize_none_type(result) == expected


# Additional test for lambda handling
def test_lambda_function() -> None:
    # Test lambda without type hints
    lambda_func = lambda: 42  # noqa: E731
    result = get_safe_type_hints(lambda_func)
    # Should infer return type
    assert result == {"return": int}

    # Test lambda that returns None
    lambda_none = lambda: None  # noqa: E731
    result = get_safe_type_hints(lambda_none)
    assert result == {"return": type(None)}


# Test for complex edge cases
def test_method_with_forward_refs_and_self() -> None:
    class Container:
        class Inner:
            def method(
                self: "Container.Inner", other: "Container"
            ) -> "Container.Inner":
                return self

    # Add the classes to the local namespace for resolution
    localns = {"Container": Container, "Container.Inner": Container.Inner}
    result = get_safe_type_hints(Container.Inner.method, localns=localns)

    # Check that we got the types
    assert "self" in result
    assert "other" in result
    assert "return" in result

    # The types should be resolved to the actual classes
    assert result["self"] == Container.Inner
    assert result["other"] == Container
    assert result["return"] == Container.Inner


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
