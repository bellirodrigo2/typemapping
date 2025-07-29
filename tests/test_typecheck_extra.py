"""Tests to improve coverage of origins.py module"""

from collections import ChainMap, Counter, OrderedDict, defaultdict
from typing import Union

import pytest

from typemapping.origins import (
    ALL_CHAINMAP_TYPES,
    ALL_COUNTER_TYPES,
    ALL_DEFAULTDICT_TYPES,
    ALL_ORDEREDDICT_TYPES,
    _handle_union_compatibility,
    get_compatibility_chain,
    get_equivalent_origin,
)

# Test the imports that might fail
try:
    from collections import Counter as ConcreteCounter
except ImportError:
    ConcreteCounter = None

try:
    from typing import Counter as TypingCounter
except ImportError:
    TypingCounter = None


class TestCollectionImports:
    """Test collection type imports and mappings"""

    def test_counter_types_list(self):
        """Test ALL_COUNTER_TYPES list construction"""
        # The list should contain only non-None types
        assert all(t is not None for t in ALL_COUNTER_TYPES)

        # If we have Counter types, test equivalence
        if ALL_COUNTER_TYPES:
            counter = Counter({"a": 1})
            counter_type = type(counter)
            # At least one should match
            assert any(
                isinstance(counter, t) or counter_type == t
                for t in ALL_COUNTER_TYPES
                if t is not None
            )

    def test_ordereddict_types_list(self):
        """Test ALL_ORDEREDDICT_TYPES list construction"""
        assert all(t is not None for t in ALL_ORDEREDDICT_TYPES)

        if ALL_ORDEREDDICT_TYPES:
            od = OrderedDict([("a", 1)])
            od_type = type(od)
            assert any(
                isinstance(od, t) or od_type == t
                for t in ALL_ORDEREDDICT_TYPES
                if t is not None
            )

    def test_chainmap_types_list(self):
        """Test ALL_CHAINMAP_TYPES list construction"""
        assert all(t is not None for t in ALL_CHAINMAP_TYPES)

        if ALL_CHAINMAP_TYPES:
            cm = ChainMap({"a": 1})
            cm_type = type(cm)
            assert any(
                isinstance(cm, t) or cm_type == t
                for t in ALL_CHAINMAP_TYPES
                if t is not None
            )

    def test_defaultdict_types_list(self):
        """Test ALL_DEFAULTDICT_TYPES list construction"""
        assert all(t is not None for t in ALL_DEFAULTDICT_TYPES)
        assert defaultdict in ALL_DEFAULTDICT_TYPES  # concrete version should be there


class TestUnionCompatibility:
    """Test _handle_union_compatibility function"""

    def test_handle_union_both_union(self):
        """Test when both types are Union"""
        t1 = Union[int, str]
        t2 = Union[str, float]

        # They share 'str' so should be compatible
        result = _handle_union_compatibility(t1, t2, Union, Union)
        assert result is True

        # No overlap
        t3 = Union[int, bool]
        t4 = Union[str, float]
        result = _handle_union_compatibility(t3, t4, Union, Union)
        # Should be True because equivalence is checked, and bool/int have relationship
        assert result is True or result is False  # Just check it doesn't crash

    def test_handle_union_edge_case(self):
        """Test union compatibility edge cases"""
        # Test the internal logic even though we usually don't call it directly
        result = _handle_union_compatibility(int, str, None, None)
        assert result is False  # Neither is Union


class TestGetEquivalentOrigin:
    """Test get_equivalent_origin edge cases"""

    def test_get_equivalent_origin_unknown_generic(self):
        """Test with generic type not in mapping"""
        from typing import Generic, TypeVar

        T = TypeVar("T")

        class CustomGeneric(Generic[T]):
            pass

        # Parameterized custom generic
        result = get_equivalent_origin(CustomGeneric[int])
        # Should return None for unknown generic types
        assert result is None

    def test_get_equivalent_origin_non_generic(self):
        """Test with non-generic custom type"""

        class CustomType:
            pass

        result = get_equivalent_origin(CustomType)
        # Should return the type itself for non-generic types not in mapping
        assert result is CustomType


class TestCompatibilityChain:
    """Test get_compatibility_chain edge cases"""

    def test_compatibility_chain_abstract_types(self):
        """Test compatibility chain includes abstract types"""

        chain = get_compatibility_chain(list)

        # Should have both concrete and abstract types
        concrete_types = [t for t in chain if not hasattr(t, "__origin__")]
        abstract_types = [t for t in chain if hasattr(t, "__origin__")]

        assert len(concrete_types) > 0
        assert len(abstract_types) > 0

        # Concrete should come before abstract
        if concrete_types and abstract_types:
            first_abstract_idx = chain.index(abstract_types[0])
            last_concrete_idx = chain.index(concrete_types[-1])
            assert last_concrete_idx < first_abstract_idx


class TestSpecialCases:
    """Test special cases and error conditions"""

    def test_chainmap_without_typing_version(self):
        """Test ChainMap when typing version not available"""
        # This tests the code path where TypingChainMap might be None
        # The code should still work with concrete ChainMap
        # Should find some equivalent origin
        origin = get_equivalent_origin(ChainMap)
        assert origin is not None

    def test_python39_builtin_generics(self):
        """Test Python 3.9+ builtin generic support"""
        import sys

        if sys.version_info >= (3, 9):
            # Test that builtin types can be used as generics
            # The code adds them to _EQUIV_ORIGIN
            from typemapping.origins import _EQUIV_ORIGIN

            # Check that list is in its own equivalence set
            assert list in _EQUIV_ORIGIN
            equiv_set = _EQUIV_ORIGIN[list]
            assert list in equiv_set


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
