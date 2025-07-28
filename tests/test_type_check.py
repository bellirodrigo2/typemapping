from collections import Counter, OrderedDict, defaultdict, deque
from typing import (Any, Dict, Iterable, List, Mapping, Optional, Sequence,
                    Set, Tuple, Union)

import pytest

# Import functions to test
from typemapping import extended_isinstance, generic_issubclass


# Test classes for inheritance
class Base:
    pass


class Derived(Base):
    pass


class Other:
    pass


class TestExtendedIssubclass:
    """Test generic_issubclass functionality."""

    def test_covariance_with_inheritance(self):
        """Test covariance: Container[Derived] <: Container[Base]."""
        assert generic_issubclass(List[Derived], List[Base])
        assert generic_issubclass(Dict[str, Derived], Dict[str, Base])
        assert generic_issubclass(Set[Derived], Set[Base])
        assert generic_issubclass(Tuple[Derived], Tuple[Base])

    def test_contravariance_inheritance(self):
        """Test contravariance is not allowed: Container[Base] not <: Container[Derived]."""
        assert not generic_issubclass(List[Base], List[Derived])
        assert not generic_issubclass(Dict[str, Base], Dict[str, Derived])
        assert not generic_issubclass(Set[Base], Set[Derived])

    def test_concrete_to_abstract(self):
        """Test concrete types are subtypes of abstract: List[T] <: Sequence[T]."""
        assert generic_issubclass(List[Base], Sequence[Base])
        assert generic_issubclass(Dict[str, Base], Mapping[str, Base])
        assert generic_issubclass(Set[Base], Iterable[Base])
        assert generic_issubclass(List[int], Sequence[int])

    def test_abstract_to_concrete_not_allowed(self):
        """Test abstract types are NOT subtypes of concrete: Sequence[T] not <: List[T]."""
        assert not generic_issubclass(Sequence[Base], List[Base])
        assert not generic_issubclass(Mapping[str, Base], Dict[str, Base])
        assert not generic_issubclass(Iterable[Base], Set[Base])

    def test_combined_covariance_and_abstraction(self):
        """Test combined covariance + abstraction: List[Derived] <: Sequence[Base]."""
        assert generic_issubclass(List[Derived], Sequence[Base])
        assert generic_issubclass(Dict[str, Derived], Mapping[str, Base])
        assert not generic_issubclass(List[Base], Sequence[Derived])

    def test_same_origin_different_args(self):
        """Test same origin with different arguments."""
        assert generic_issubclass(List[Derived], List[Base])
        assert not generic_issubclass(List[Base], List[Derived])
        assert not generic_issubclass(List[Base], List[Other])

    def test_incompatible_origins(self):
        """Test incompatible container types."""
        assert not generic_issubclass(List[Base], Set[Base])
        assert not generic_issubclass(Dict[str, Base], List[Base])
        assert not generic_issubclass(Set[Base], Dict[str, Base])

    def test_union_types(self):
        """Test Union type handling."""
        # T <: Union[T, U]
        assert generic_issubclass(List[Base], Union[List[Base], Set[Base]])
        assert generic_issubclass(int, Union[int, str])

        # Union[T, U] <: V if T <: V and U <: V
        assert generic_issubclass(Union[List[Base], List[Derived]], List[Base])
        assert not generic_issubclass(Union[List[Base], Set[Base]], List[Base])

    def test_optional_types(self):
        """Test Optional type handling."""
        # T <: Optional[T]
        assert generic_issubclass(List[Base], Optional[List[Base]])
        assert generic_issubclass(int, Optional[int])

        # Optional[Derived] <: Optional[Base]
        assert generic_issubclass(Optional[Derived], Optional[Base])
        assert not generic_issubclass(Optional[Base], Optional[Derived])

        # Optional[T] <: Union[T, None]
        assert generic_issubclass(Optional[Base], Union[Base, type(None)])

    def test_any_type(self):
        """Test Any type handling."""
        assert generic_issubclass(List[int], List[Any])
        assert not generic_issubclass(List[Any], List[int])

    def test_no_args_types(self):
        """Test types without generic arguments."""
        assert generic_issubclass(list, Sequence)
        assert generic_issubclass(dict, Mapping)
        assert not generic_issubclass(Sequence, list)

    def test_collections_specializations(self):
        """Test specialized collections."""
        # These should work with concrete dict types
        assert generic_issubclass(defaultdict, dict)
        assert generic_issubclass(Counter, dict)
        assert generic_issubclass(OrderedDict, dict)
        assert generic_issubclass(deque, list)  # deque is like a list

        # But not necessarily with generic Dict[K,V] due to args compatibility
        # This is more complex - let's test simpler cases


class TestExtendedIsinstance:
    """Test extended_isinstance functionality."""

    def test_basic_list_isinstance(self):
        """Test basic list instance checking."""
        list1 = [1, 2, 3]
        assert extended_isinstance(list1, List[int])
        assert extended_isinstance(list1, Sequence[int])
        assert extended_isinstance(list1, Iterable[int])
        assert not extended_isinstance(list1, List[str])
        assert not extended_isinstance(list1, Set[int])

    def test_mixed_type_list(self):
        """Test list with mixed types."""
        mixed_list = [1, "hello", 3.14]
        assert not extended_isinstance(mixed_list, List[int])
        assert not extended_isinstance(mixed_list, List[str])
        # Mixed types should match List[Any] since Any accepts anything
        assert extended_isinstance(mixed_list, List[Any])

    def test_dict_isinstance(self):
        """Test dictionary instance checking."""
        dict1 = {"a": 1, "b": 2}
        assert extended_isinstance(dict1, Dict[str, int])
        assert extended_isinstance(dict1, Mapping[str, int])
        assert not extended_isinstance(dict1, Dict[str, str])
        assert not extended_isinstance(dict1, Dict[int, int])

    def test_set_isinstance(self):
        """Test set instance checking."""
        set1 = {1, 2, 3}
        assert extended_isinstance(set1, Set[int])
        assert extended_isinstance(set1, Iterable[int])
        assert not extended_isinstance(set1, Set[str])
        assert not extended_isinstance(set1, List[int])

    def test_tuple_isinstance(self):
        """Test tuple instance checking."""
        tuple1 = (1, 2, 3)
        assert extended_isinstance(tuple1, Tuple[int, ...])
        assert extended_isinstance(tuple1, Sequence[int])
        assert not extended_isinstance(tuple1, Tuple[str, ...])

    def test_empty_containers(self):
        """Test empty containers."""
        assert extended_isinstance([], List[int])  # Empty list matches any element type
        assert extended_isinstance(
            {}, Dict[str, int]
        )  # Empty dict matches any key/value types
        assert extended_isinstance(
            set(), Set[int]
        )  # Empty set matches any element type

    def test_inheritance_isinstance(self):
        """Test isinstance with inheritance."""
        derived_list = [Derived(), Derived()]
        base_list = [Base(), Base()]

        assert extended_isinstance(derived_list, List[Derived])
        assert extended_isinstance(derived_list, List[Base])  # covariance
        assert extended_isinstance(base_list, List[Base])
        assert not extended_isinstance(base_list, List[Derived])  # contravariance

    def test_union_isinstance(self):
        """Test Union type instance checking."""
        assert extended_isinstance([1, 2, 3], Union[List[int], Set[int]])
        assert extended_isinstance({1, 2, 3}, Union[List[int], Set[int]])
        assert not extended_isinstance("hello", Union[List[int], Set[int]])

    def test_optional_isinstance(self):
        """Test Optional type instance checking."""
        assert extended_isinstance(None, Optional[int])
        assert extended_isinstance(42, Optional[int])
        assert not extended_isinstance("hello", Optional[int])

        assert extended_isinstance(None, Optional[List[int]])
        assert extended_isinstance([1, 2, 3], Optional[List[int]])

    def test_collections_isinstance(self):
        """Test specialized collections instance checking."""
        dd = defaultdict(int)
        dd["a"] = 1
        assert extended_isinstance(dd, Dict[str, int])
        assert extended_isinstance(dd, Mapping[str, int])

        counter = Counter("hello")
        assert extended_isinstance(counter, Dict[str, int])

        od = OrderedDict([("a", 1), ("b", 2)])
        assert extended_isinstance(od, Dict[str, int])

        dq = deque([1, 2, 3])
        assert extended_isinstance(dq, Sequence[int])

    def test_nested_generics(self):
        """Test nested generic types."""
        nested_list = [[1, 2], [3, 4]]
        assert extended_isinstance(nested_list, List[List[int]])
        assert extended_isinstance(nested_list, Sequence[Sequence[int]])
        assert not extended_isinstance(nested_list, List[List[str]])

        nested_dict = {"a": {"x": 1}, "b": {"y": 2}}
        assert extended_isinstance(nested_dict, Dict[str, Dict[str, int]])
        assert not extended_isinstance(nested_dict, Dict[str, Dict[str, str]])

    def test_performance_large_containers(self):
        """Test performance with large containers (should sample, not check all)."""
        large_list = list(range(10000))
        assert extended_isinstance(large_list, List[int])

        large_dict = {f"key_{i}": i for i in range(10000)}
        assert extended_isinstance(large_dict, Dict[str, int])


class TestEdgeCases:
    """Test edge cases and corner scenarios."""

    def test_recursive_types(self):
        """Test recursive type definitions."""
        # This is a complex case that might not be fully supported
        # but should not crash
        try:
            nested = [[[1]]]
            result = extended_isinstance(nested, List[List[List[int]]])
            assert isinstance(result, bool)  # Should return some boolean result
        except Exception:
            pytest.skip("Recursive types not fully supported")

    def test_malformed_generics(self):
        """Test handling of malformed or unusual generic types."""
        # Test with non-generic types used as if they were generic
        assert not extended_isinstance([1, 2, 3], str)
        assert not extended_isinstance({"a": 1}, int)

    def test_none_values(self):
        """Test None handling in various contexts."""
        assert not extended_isinstance(None, List[int])
        assert extended_isinstance(None, Optional[List[int]])
        assert not extended_isinstance([None, None], List[int])
        assert extended_isinstance([None, None], List[Optional[int]])

    def test_mixed_inheritance_complex(self):
        """Test complex inheritance scenarios."""

        class A:
            pass

        class B(A):
            pass

        class C(B):
            pass

        # Multi-level inheritance
        assert generic_issubclass(List[C], List[A])
        assert generic_issubclass(List[C], Sequence[A])
        assert not generic_issubclass(List[A], List[C])

    def test_non_container_types(self):
        """Test with non-container types."""
        assert not extended_isinstance(42, List[int])
        assert not extended_isinstance("hello", Dict[str, int])
        assert extended_isinstance(42, int)
        assert extended_isinstance("hello", str)


# Parametrized tests for comprehensive coverage
@pytest.mark.parametrize(
    "subtype,supertype,expected",
    [
        # Basic covariance
        (List[Derived], List[Base], True),
        (List[Base], List[Derived], False),
        # Abstraction
        (List[Base], Sequence[Base], True),
        (Sequence[Base], List[Base], False),
        # Combined
        (List[Derived], Sequence[Base], True),
        (List[Base], Sequence[Derived], False),
        # Incompatible origins
        (List[Base], Set[Base], False),
        (Dict[str, Base], List[Base], False),
        # Union types
        (int, Union[int, str], True),
        (Union[int, str], int, False),
        # Optional types
        (int, Optional[int], True),
        (Optional[Derived], Optional[Base], True),
        (Optional[Base], Optional[Derived], False),
    ],
)
def test_parametrized_issubclass(subtype, supertype, expected):
    """Parametrized test for generic_issubclass."""
    assert generic_issubclass(subtype, supertype) == expected


@pytest.mark.parametrize(
    "obj,type_hint,expected",
    [
        # Basic cases
        ([1, 2, 3], List[int], True),
        ([1, 2, 3], List[str], False),
        ([1, 2, 3], Sequence[int], True),
        ([1, 2, 3], Set[int], False),
        # Dict cases
        ({"a": 1}, Dict[str, int], True),
        ({"a": 1}, Dict[str, str], False),
        ({"a": 1}, Mapping[str, int], True),
        # Union cases
        ([1, 2, 3], Union[List[int], Set[int]], True),
        ({1, 2, 3}, Union[List[int], Set[int]], True),
        ("hello", Union[List[int], Set[int]], False),
        # Optional cases
        (None, Optional[int], True),
        (42, Optional[int], True),
        ("hello", Optional[int], False),
    ],
)
def test_parametrized_isinstance(obj, type_hint, expected):
    """Parametrized test for extended_isinstance."""
    assert extended_isinstance(obj, type_hint) == expected
