"""
Type compatibility and equivalence system.

This module provides sophisticated type checking that handles:
- Generic type equivalence (List[int] ~ Sequence[int])
- Collection specializations (Counter ~ dict)
- Union type compatibility
- Cross-version type compatibility
"""

import sys
# Basic collections
from collections import defaultdict, deque
from typing import (Any, Callable, Collection, Dict, FrozenSet, List, Optional,
                    Set, Tuple, Type, Union, get_args, get_origin)

# ===== RESOLVE TYPING vs COLLECTIONS CONFLICTS =====

# Import concrete collections with aliases to avoid conflicts
try:
    from collections import ChainMap as ConcreteChainMap
    from collections import Counter as ConcreteCounter
    from collections import OrderedDict as ConcreteOrderedDict
except ImportError:
    ConcreteCounter = None  # type: ignore
    ConcreteOrderedDict = None  # type: ignore
    ConcreteChainMap = None  # type: ignore

# Import typing versions with aliases
try:
    from typing import ChainMap as TypingChainMap
    from typing import Counter as TypingCounter
    from typing import DefaultDict as TypingDefaultDict
    from typing import OrderedDict as TypingOrderedDict
except ImportError:
    TypingCounter = None  # type: ignore
    TypingOrderedDict = None  # type: ignore
    TypingChainMap = None  # type: ignore
    TypingDefaultDict = None  # type: ignore

# ===== COLLECTIONS.ABC IMPORTS =====

try:
    # Python 3.8+ compatibility
    from collections.abc import Callable as AbcCallable
    from collections.abc import Container as AbcContainer
    from collections.abc import Iterable as AbcIterable
    from collections.abc import Mapping as AbcMapping
    from collections.abc import MutableMapping as AbcMutableMapping
    from collections.abc import MutableSequence, MutableSet
    from collections.abc import Sequence as AbcSequence
    from collections.abc import Set as AbcSet
except ImportError:
    # Fallback - use typing versions directly
    from typing import Callable as AbcCallable  # type: ignore
    from typing import Container as AbcContainer  # type: ignore
    from typing import Iterable as AbcIterable  # type: ignore
    from typing import Mapping as AbcMapping  # type: ignore
    from typing import MutableMapping as AbcMutableMapping  # type: ignore
    from typing import Sequence as AbcSequence  # type: ignore
    from typing import Set as AbcSet  # type: ignore
    from typing import MutableSequence, MutableSet  # type: ignore

# ===== UNIFIED TYPE MAPPINGS =====

# All Counter types (both concrete and typing versions) - ORDERED LIST
ALL_COUNTER_TYPES = list(filter(None, [TypingCounter, ConcreteCounter]))  # typing first

# All OrderedDict types - ORDERED LIST
ALL_ORDEREDDICT_TYPES = list(
    filter(None, [TypingOrderedDict, ConcreteOrderedDict])
)  # typing first

# All ChainMap types - ORDERED LIST
ALL_CHAINMAP_TYPES = list(
    filter(None, [TypingChainMap, ConcreteChainMap])
)  # typing first

# All DefaultDict types - ORDERED LIST (concrete first for defaultdict)
ALL_DEFAULTDICT_TYPES = list(
    filter(None, [defaultdict, TypingDefaultDict])
)  # concrete first

# Complete mapping of type equivalences
_EQUIV_ORIGIN: Dict[Type[Any], Collection[Type[Any]]] = {
    # Sequences
    list: {list, List, AbcSequence, MutableSequence, AbcIterable, AbcContainer},
    tuple: {tuple, Tuple, AbcSequence, AbcIterable, AbcContainer}, #type:ignore
    # Sets
    set: {set, Set, AbcSet, MutableSet, AbcIterable, AbcContainer},
    frozenset: {frozenset, FrozenSet, AbcSet, AbcIterable, AbcContainer},
    # Mappings
    dict: {dict, Dict, AbcMapping, AbcMutableMapping, AbcContainer},
    # Basic specializations
    defaultdict: {defaultdict, dict, Dict, AbcMapping, AbcMutableMapping, AbcContainer},
    deque: {deque, MutableSequence, AbcSequence, AbcIterable, AbcContainer},
    # Abstract types enable compatibility
    AbcSequence: {
        deque,
        list,
        tuple,
        AbcSequence,
        MutableSequence,
        AbcIterable,
        AbcContainer,
    },
    # Callables
    type(lambda: None): {type(lambda: None), Callable, AbcCallable}, #type:ignore
}

# Add all Counter variants to mapping - DETERMINISTIC ORDER
counter_equiv_set = {dict, Dict, AbcMapping, AbcMutableMapping, AbcContainer}
for counter_type in ALL_COUNTER_TYPES:
    counter_equiv_set.add(counter_type)  # type: ignore
for counter_type in ALL_COUNTER_TYPES:  # Iterates in deterministic order
    _EQUIV_ORIGIN[counter_type] = counter_equiv_set.copy()

# Add all OrderedDict variants to mapping - DETERMINISTIC ORDER
ordereddict_equiv_set = {dict, Dict, AbcMapping, AbcMutableMapping, AbcContainer}
for ordereddict_type in ALL_ORDEREDDICT_TYPES:
    ordereddict_equiv_set.add(ordereddict_type)  # type: ignore
for ordereddict_type in ALL_ORDEREDDICT_TYPES:  # Iterates in deterministic order
    _EQUIV_ORIGIN[ordereddict_type] = ordereddict_equiv_set.copy()

# Add all ChainMap variants to mapping - DETERMINISTIC ORDER
chainmap_equiv_set = {AbcMapping, AbcMutableMapping, AbcContainer}
for chainmap_type in ALL_CHAINMAP_TYPES:
    chainmap_equiv_set.add(chainmap_type)  # type: ignore
for chainmap_type in ALL_CHAINMAP_TYPES:  # Iterates in deterministic order
    _EQUIV_ORIGIN[chainmap_type] = chainmap_equiv_set.copy()

# Add all DefaultDict variants to mapping - DETERMINISTIC ORDER
defaultdict_equiv_set = {dict, Dict, AbcMapping, AbcMutableMapping, AbcContainer}
for defaultdict_type in ALL_DEFAULTDICT_TYPES:
    defaultdict_equiv_set.add(defaultdict_type)  # type: ignore
for defaultdict_type in ALL_DEFAULTDICT_TYPES:  # Iterates in deterministic order
    _EQUIV_ORIGIN[defaultdict_type] = defaultdict_equiv_set.copy()

# Python 3.9+ support for built-in types as generics
if sys.version_info >= (3, 9):
    builtin_generic_types = {list, dict, set, tuple, frozenset}
    for builtin_type in builtin_generic_types:
        if builtin_type in _EQUIV_ORIGIN:
            existing_set = set(_EQUIV_ORIGIN[builtin_type])  # type: ignore
            existing_set.add(builtin_type)
            _EQUIV_ORIGIN[builtin_type] = existing_set


def is_equivalent_origin(t1: Type[Any], t2: Type[Any]) -> bool:
    """
    Check if two types have equivalent/compatible origins.

    Args:
        t1, t2: Types to compare

    Returns:
        True if types are compatible

    Examples:
        >>> is_equivalent_origin(List[int], list)
        True
        >>> is_equivalent_origin(Dict[str, int], Mapping[str, int])
        True
        >>> is_equivalent_origin(Counter[str], dict)  # Both typing and collections Counter
        True
    """
    o1, o2 = get_origin(t1) or t1, get_origin(t2) or t2

    # Direct comparison
    if o1 == o2:
        return True

    # Search in equivalences
    for equiv_set in _EQUIV_ORIGIN.values():
        if o1 in equiv_set and o2 in equiv_set:
            return True

    # Special cases: Union types
    if o1 is Union or o2 is Union:
        return _handle_union_compatibility(t1, t2, o1, o2)

    return False


def get_equivalent_origin(t: Type[Any]) -> Optional[Type[Any]]:
    """
    Return the most specific 'canonical' type for a given type.

    Args:
        t: Type to find equivalent for

    Returns:
        Most specific canonical type or None

    Examples:
        >>> get_equivalent_origin(List[int])
        <class 'list'>
        >>> get_equivalent_origin(Counter[str])  # Returns typing.Counter
        typing.Counter
        >>> get_equivalent_origin(defaultdict)  # Returns collections.defaultdict
        <class 'collections.defaultdict'>
    """
    origin = get_origin(t) or t

    # Special handling for collection types to ensure deterministic results
    # Prefer typing versions for Counter, OrderedDict, ChainMap
    # Prefer concrete version for defaultdict (more commonly used)
    if origin in ALL_COUNTER_TYPES:
        return ALL_COUNTER_TYPES[0]  # typing.Counter
    if origin in ALL_ORDEREDDICT_TYPES:
        return ALL_ORDEREDDICT_TYPES[0]  # typing.OrderedDict
    if origin in ALL_CHAINMAP_TYPES:
        return ALL_CHAINMAP_TYPES[0]  # typing.ChainMap
    if origin in ALL_DEFAULTDICT_TYPES:
        return ALL_DEFAULTDICT_TYPES[0]  # collections.defaultdict

    # Find the most specific type (first in hierarchy)
    for canonical, equiv_set in _EQUIV_ORIGIN.items():
        if origin in equiv_set:
            return canonical

    # For types not in our equivalence mapping, return None only if it's a generic type
    if get_origin(t) is not None:
        return None

    # For concrete types not in mapping, return the type itself
    return origin


def are_args_compatible(t1: Type[Any], t2: Type[Any]) -> bool:
    """
    Check if generic type arguments are compatible.

    Args:
        t1, t2: Generic types to compare arguments

    Returns:
        True if arguments are compatible
    """
    args1, args2 = get_args(t1), get_args(t2)

    # If both have no args, they're compatible
    if not args1 and not args2:
        return True

    # If one has args and other doesn't, not compatible
    if bool(args1) != bool(args2):
        return False

    # If different number of args, not compatible
    if len(args1) != len(args2):
        return False

    # Compare each argument recursively
    return all(is_fully_compatible(arg1, arg2) for arg1, arg2 in zip(args1, args2))


def is_fully_compatible(t1: Type[Any], t2: Type[Any]) -> bool:
    """
    Check full compatibility including generic type arguments.

    Args:
        t1, t2: Types to compare completely

    Returns:
        True if fully compatible

    Examples:
        >>> is_fully_compatible(List[int], Sequence[int])
        True
        >>> is_fully_compatible(List[int], List[str])
        False
    """
    if not is_equivalent_origin(t1, t2):
        return False

    return are_args_compatible(t1, t2)


def _handle_union_compatibility(t1: Type[Any], t2: Type[Any], o1: Any, o2: Any) -> bool:
    """Handle Union type compatibility."""
    if o1 is Union and o2 is not Union:
        # Check if t2 is compatible with any Union member
        return any(is_equivalent_origin(arg, t2) for arg in get_args(t1))
    elif o2 is Union and o1 is not Union:
        # Check if t1 is compatible with any Union member
        return any(is_equivalent_origin(t1, arg) for arg in get_args(t2))
    elif o1 is Union and o2 is Union:
        # Both are Union - check intersection
        args1, args2 = get_args(t1), get_args(t2)
        return any(is_equivalent_origin(arg1, arg2) for arg1 in args1 for arg2 in args2)
    return False


def get_compatibility_chain(t: Type[Any]) -> List[Type[Any]]:
    """
    Return the compatibility chain of a type (from most specific to most general).

    Args:
        t: Type to get chain for

    Returns:
        Ordered list of compatible types
    """
    origin = get_origin(t) or t

    for canonical, equiv_set in _EQUIV_ORIGIN.items():
        if origin in equiv_set:
            # Sort by specificity (concrete types first)
            concrete = [typ for typ in equiv_set if not hasattr(typ, "__origin__")]
            abstract = [typ for typ in equiv_set if hasattr(typ, "__origin__")]
            return concrete + abstract

    return [origin]


def debug_type_info(t: Type[Any]) -> Dict[str, Any]:
    """
    Return detailed information about a type for debugging.

    Args:
        t: Type to inspect

    Returns:
        Dictionary with type information
    """
    return {
        "type": t,
        "origin": get_origin(t),
        "args": get_args(t),
        "equivalent_origin": get_equivalent_origin(t),
        "compatibility_chain": get_compatibility_chain(t),
        "is_generic": bool(get_args(t)),
        "module": getattr(t, "__module__", None),
    }