from collections import defaultdict, deque
from typing import (Any, Callable, ChainMap, Collection, Counter, DefaultDict,
                    Deque, Dict, FrozenSet, Generator, List, Optional,
                    OrderedDict, Set, Tuple, Type, Union, get_args, get_origin)

try:
    # Python 3.8+ compatibility
    from collections.abc import AsyncGenerator as AbcAsyncGenerator
    from collections.abc import AsyncIterator as AbcAsyncIterator
    from collections.abc import Awaitable as AbcAwaitable
    from collections.abc import Callable as AbcCallable
    from collections.abc import Container as AbcContainer
    from collections.abc import Coroutine as AbcCoroutine
    from collections.abc import Generator as AbcGenerator
    from collections.abc import Iterable as AbcIterable
    from collections.abc import Iterator as AbcIterator
    from collections.abc import Mapping as AbcMapping
    from collections.abc import MutableMapping as AbcMutableMapping
    from collections.abc import MutableSequence, MutableSet
    from collections.abc import Sequence as AbcSequence
    from collections.abc import Set as AbcSet
except ImportError:
    # Fallback for older Python versions
    from collections import Callable as AbcCallable
    from collections import Container as AbcContainer
    from collections import Generator as AbcGenerator
    from collections import Iterable as AbcIterable
    from collections import Iterator as AbcIterator
    from collections import Mapping as AbcMapping
    from collections import MutableMapping as AbcMutableMapping
    from collections import MutableSequence, MutableSet
    from collections import Sequence as AbcSequence
    from collections import Set as AbcSet

    # Mock missing types for older versions
    AbcCoroutine = AbcAwaitable = AbcAsyncIterator = AbcAsyncGenerator = type(None)

import sys

# Complete mapping of type equivalences
_EQUIV_ORIGIN: Dict[Type[Any], Collection[Type[Any]]] = {
    # Sequences
    list: {list, List, AbcSequence, MutableSequence, AbcIterable, AbcContainer},
    tuple: {tuple, Tuple, AbcSequence, AbcIterable, AbcContainer},
    # Sets
    set: {set, Set, AbcSet, MutableSet, AbcIterable, AbcContainer},
    frozenset: {frozenset, FrozenSet, AbcSet, AbcIterable, AbcContainer},
    # Mappings
    dict: {dict, Dict, AbcMapping, AbcMutableMapping, AbcContainer},
    # Dict specializations
    defaultdict: {
        defaultdict,
        DefaultDict,
        dict,
        Dict,
        AbcMapping,
        AbcMutableMapping,
        AbcContainer,
    },
    OrderedDict: {OrderedDict, dict, Dict, AbcMapping, AbcMutableMapping, AbcContainer},
    Counter: {Counter, dict, Dict, AbcMapping, AbcMutableMapping, AbcContainer},
    ChainMap: {ChainMap, AbcMapping, AbcMutableMapping, AbcContainer},
    # Collections specializations
    deque: {deque, Deque, MutableSequence, AbcSequence, AbcIterable, AbcContainer},
    # Callables
    type(lambda: None): {type(lambda: None), Callable, AbcCallable},
    # Generators and Async (when available)
    type(x for x in []): {
        type(x for x in []),
        Generator,
        AbcGenerator,
        AbcIterator,
        AbcIterable,
    },
    # Add abstract types to enable deque -> Sequence compatibility
    AbcSequence: {
        deque,
        list,
        tuple,
        AbcSequence,
        MutableSequence,
        AbcIterable,
        AbcContainer,
    },
}

# Python 3.9+ support for built-in types as generics
if sys.version_info >= (3, 9):
    _EQUIV_ORIGIN.update(
        {
            list: _EQUIV_ORIGIN[list] | {list},  # list[int] in Python 3.9+
            dict: _EQUIV_ORIGIN[dict] | {dict},  # dict[str, int] in Python 3.9+
            set: _EQUIV_ORIGIN[set] | {set},  # set[int] in Python 3.9+
            tuple: _EQUIV_ORIGIN[tuple] | {tuple},  # tuple[int, ...] in Python 3.9+
        }
    )


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
        >>> is_equivalent_origin(Set[int], Iterable[int])
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
        >>> get_equivalent_origin(Sequence[str])
        <class 'list'>  # more specific than Sequence
    """
    origin = get_origin(t) or t

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

    Examples:
        >>> get_compatibility_chain(List[int])
        [<class 'list'>, typing.Sequence, typing.Iterable, typing.Container]
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
