from collections import defaultdict, deque
from collections.abc import Iterable as AbcIterable
from collections.abc import Mapping as AbcMapping
from collections.abc import Sequence as AbcSequence
from typing import (
    Callable,
    Container,
    Counter,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    OrderedDict,
    Sequence,
    Set,
    Tuple,
    Union,
)

import pytest

# Import the functions to test
from typemapping import (
    are_args_compatible,
    debug_type_info,
    get_compatibility_chain,
    get_equivalent_origin,
    is_equivalent_origin,
    is_fully_compatible,
)


class TestIsEquivalentOrigin:
    """Test basic origin equivalence."""

    def test_identical_types(self):
        """Test identical types are equivalent."""
        assert is_equivalent_origin(List[int], List[int])
        assert is_equivalent_origin(Dict[str, int], Dict[str, int])
        assert is_equivalent_origin(str, str)

    def test_concrete_vs_typing(self):
        """Test concrete types vs typing equivalents."""
        assert is_equivalent_origin(list, List[int])
        assert is_equivalent_origin(dict, Dict[str, int])
        assert is_equivalent_origin(set, Set[str])
        assert is_equivalent_origin(tuple, Tuple[int, str])

    def test_abstract_compatibility(self):
        """Test abstract base class compatibility."""
        assert is_equivalent_origin(List[int], Sequence[int])
        assert is_equivalent_origin(Dict[str, int], Mapping[str, int])
        assert is_equivalent_origin(Set[str], Iterable[str])
        assert is_equivalent_origin(List[int], Container[int])

    def test_collections_specializations(self):
        """Test specialized collections compatibility."""
        assert is_equivalent_origin(defaultdict, Dict[str, int])
        assert is_equivalent_origin(Counter[str], Dict[str, int])
        assert is_equivalent_origin(OrderedDict[str, int], Mapping[str, int])
        assert is_equivalent_origin(deque, Sequence[int])

    def test_union_compatibility(self):
        """Test Union type compatibility."""
        assert is_equivalent_origin(Union[str, int], str)
        assert is_equivalent_origin(Union[str, int], int)
        assert is_equivalent_origin(str, Union[str, int])
        assert is_equivalent_origin(Union[List[int], Set[int]], List[int])

    def test_incompatible_types(self):
        """Test types that should not be compatible."""
        assert not is_equivalent_origin(List[int], Set[int])
        assert not is_equivalent_origin(Dict[str, int], List[int])
        assert not is_equivalent_origin(str, int)
        assert not is_equivalent_origin(type(lambda: None), List[int])


class TestGetEquivalentOrigin:
    """Test canonical origin retrieval."""

    def test_typing_to_concrete(self):
        """Test typing types return concrete equivalents."""
        assert get_equivalent_origin(List[int]) is list
        assert get_equivalent_origin(Dict[str, int]) is dict
        assert get_equivalent_origin(Set[str]) is set
        assert get_equivalent_origin(Tuple[int, str]) is tuple

    def test_abstract_to_concrete(self):
        """Test abstract types return concrete equivalents."""
        assert get_equivalent_origin(Sequence[int]) is list
        assert get_equivalent_origin(Mapping[str, int]) is dict
        assert get_equivalent_origin(Iterable[str]) is list

    def test_concrete_types(self):
        """Test concrete types return themselves."""
        assert get_equivalent_origin(list) is list
        assert get_equivalent_origin(dict) is dict
        assert (
            get_equivalent_origin(str) is str
        )  # str returns itself (not in _EQUIV_ORIGIN)

    def test_unknown_types(self):
        """Test unknown types return themselves for concrete types, None for generics."""
        assert get_equivalent_origin(int) is int  # concrete type
        assert get_equivalent_origin(str) is str  # concrete type
        assert get_equivalent_origin(float) is float  # concrete type


class TestAreArgsCompatible:
    """Test generic argument compatibility."""

    def test_same_args(self):
        """Test identical arguments are compatible."""
        assert are_args_compatible(List[int], List[int])
        assert are_args_compatible(Dict[str, int], Dict[str, int])
        assert are_args_compatible(Tuple[int, str], Tuple[int, str])

    def test_different_args(self):
        """Test different arguments are not compatible."""
        assert not are_args_compatible(List[int], List[str])
        assert not are_args_compatible(Dict[str, int], Dict[str, str])
        assert not are_args_compatible(Tuple[int], Tuple[int, str])

    def test_no_args(self):
        """Test types without arguments."""
        assert are_args_compatible(list, dict)  # Both no args
        assert are_args_compatible(List, Dict)  # Both no args

    def test_mixed_args(self):
        """Test one with args, one without."""
        assert not are_args_compatible(List[int], List)  # One has args, one doesn't
        assert not are_args_compatible(
            Dict, Dict[str, int]
        )  # One has args, one doesn't


class TestIsFullyCompatible:
    """Test complete compatibility including arguments."""

    def test_fully_compatible(self):
        """Test fully compatible types."""
        assert is_fully_compatible(List[int], Sequence[int])
        assert is_fully_compatible(Dict[str, int], Mapping[str, int])
        assert is_fully_compatible(Set[str], Iterable[str])

    def test_origin_compatible_args_not(self):
        """Test compatible origins but incompatible arguments."""
        assert not is_fully_compatible(List[int], List[str])
        assert not is_fully_compatible(Dict[str, int], Dict[str, str])

    def test_different_origins(self):
        """Test incompatible origins."""
        assert not is_fully_compatible(List[int], Set[int])
        assert not is_fully_compatible(Dict[str, int], Tuple[str])


class TestGetCompatibilityChain:
    """Test compatibility chain generation."""

    def test_list_chain(self):
        """Test list compatibility chain."""
        chain = get_compatibility_chain(List[int])
        assert list in chain
        assert AbcSequence in chain or Sequence in chain
        # Check for any iterable type in chain
        iterable_types = {Iterable, AbcIterable}
        assert any(it in chain for it in iterable_types)

    def test_dict_chain(self):
        """Test dict compatibility chain."""
        chain = get_compatibility_chain(Dict[str, int])
        assert dict in chain
        assert AbcMapping in chain or Mapping in chain

    def test_unknown_type_chain(self):
        """Test unknown type returns itself."""
        chain = get_compatibility_chain(str)
        assert str in chain


class TestDebugTypeInfo:
    """Test debug information generation."""

    def test_generic_type_info(self):
        """Test debug info for generic types."""
        info = debug_type_info(List[int])
        assert info["type"] == List[int]
        assert info["origin"] is list
        assert info["args"] == (int,)
        assert info["is_generic"] is True
        assert info["equivalent_origin"] is list

    def test_concrete_type_info(self):
        """Test debug info for concrete types."""
        info = debug_type_info(list)
        assert info["type"] is list
        assert info["origin"] is None
        assert info["args"] == ()
        assert info["is_generic"] is False

    def test_union_type_info(self):
        """Test debug info for Union types."""
        info = debug_type_info(Union[str, int])
        assert info["type"] == Union[str, int]
        assert info["args"] == (str, int)


class TestEdgeCases:
    """Test edge cases and corner scenarios."""

    def test_nested_generics(self):
        """Test nested generic types."""
        assert is_equivalent_origin(List[Dict[str, int]], Sequence[Mapping[str, int]])
        assert not is_fully_compatible(List[Dict[str, int]], List[Dict[str, str]])

    def test_optional_types(self):
        """Test Optional (Union with None) types."""
        assert is_equivalent_origin(Optional[str], Union[str, type(None)])
        assert is_equivalent_origin(Union[str, None], str)

    def test_complex_unions(self):
        """Test complex Union scenarios."""
        assert is_equivalent_origin(Union[List[int], Set[int]], Iterable[int])
        assert is_equivalent_origin(Union[str, int, float], str)

    def test_callable_types(self):
        """Test Callable type compatibility."""
        func_type = type(lambda: None)
        assert is_equivalent_origin(func_type, Callable)

    def test_none_types(self):
        """Test None and NoneType handling."""
        assert is_equivalent_origin(type(None), type(None))
        assert not is_equivalent_origin(type(None), str)


# Parametrized tests for comprehensive coverage
@pytest.mark.parametrize(
    "t1,t2,expected",
    [
        # Basic equivalences
        (List[int], list, True),
        (Dict[str, int], dict, True),
        (Set[str], set, True),
        (Tuple[int], tuple, True),
        # Abstract compatibility
        (List[int], Sequence[int], True),
        (Dict[str, int], Mapping[str, int], True),
        (Set[str], Iterable[str], True),
        # Collections specializations
        (defaultdict, dict, True),
        (Counter, dict, True),
        (OrderedDict, dict, True),
        (deque, Sequence, True),  # Now should work with AbcSequence mapping
        # Union types
        (Union[str, int], str, True),
        (Union[str, int], int, True),
        (str, Union[str, int], True),
        # Incompatible types - these should be False
        (List[int], Set[int], False),
        (Dict[str, int], Tuple[int], False),  # Changed from List to Tuple
        (str, int, False),
    ],
)
def test_parametrized_equivalence(t1, t2, expected):
    """Parametrized test for type equivalence."""
    assert is_equivalent_origin(t1, t2) == expected


@pytest.mark.parametrize(
    "type_input,expected_origin",
    [
        (List[int], list),
        (Dict[str, int], dict),
        (Set[str], set),
        (Sequence[int], list),
        (Mapping[str, int], dict),
        (Iterable[str], list),
        (defaultdict, defaultdict),
        (Counter, Counter),
    ],
)
def test_parametrized_get_origin(type_input, expected_origin):
    """Parametrized test for getting equivalent origins."""
    assert get_equivalent_origin(type_input) == expected_origin
