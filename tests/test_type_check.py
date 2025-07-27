import inspect
from typing import Any, DefaultDict, Type, Union, get_args, get_origin

from typemapping.origins import is_equivalent_origin
from typemapping.type_check import extended_isinstance, extended_issubclass


def _is_union_type(t: Type[Any]) -> bool:
    """Check if type is a Union."""
    return get_origin(t) is Union


def _is_optional_type(t: Type[Any]) -> bool:
    """Check if type is Optional[T] (Union[T, None])."""
    if not _is_union_type(t):
        return False
    args = get_args(t)
    return len(args) == 2 and type(None) in args


def _get_optional_inner_type(t: Type[Any]) -> Type[Any]:
    """Get the inner type from Optional[T]."""
    args = get_args(t)
    return next(arg for arg in args if arg is not type(None))


def _is_subtype_origin(sub_origin: Type[Any], super_origin: Type[Any]) -> bool:
    """
    Check if sub_origin is a subtype of super_origin using our equivalence system.

    Rules:
    - Concrete types are subtypes of their abstractions (list <: Sequence)
    - Abstract types are NOT subtypes of concrete types (Sequence not <: list)
    - Equivalent types are subtypes of each other
    """
    # Direct equality
    if sub_origin == super_origin:
        return True

    # Special handling for collections specializations
    if _is_collection_specialization_subtype(sub_origin, super_origin):
        return True

    # Use our equivalence system to check compatibility
    if is_equivalent_origin(sub_origin, super_origin):
        # Additional check: concrete -> abstract is allowed, but not abstract -> concrete
        return _is_abstraction_compatible(sub_origin, super_origin)

    # Fallback to regular issubclass for non-generic types
    try:
        if inspect.isclass(sub_origin) and inspect.isclass(super_origin):
            return issubclass(sub_origin, super_origin)
    except TypeError:
        pass

    return False


def _is_collection_specialization_subtype(
    sub_origin: Type[Any], super_origin: Type[Any]
) -> bool:
    """Handle special cases for collection specializations."""
    from collections import Counter, OrderedDict, defaultdict, deque

    # Map specializations to their base types
    specialization_map = {
        defaultdict: dict,
        Counter: dict,
        OrderedDict: dict,
        deque: list,  # deque behaves like a list
    }

    if sub_origin in specialization_map:
        base_type = specialization_map[sub_origin]
        return base_type == super_origin or is_equivalent_origin(
            base_type, super_origin
        )

    return False


def _is_abstraction_compatible(sub_origin: Type[Any], super_origin: Type[Any]) -> bool:
    """
    Check if sub_origin can be a subtype of super_origin based on abstraction level.

    Concrete types (list, dict) can be subtypes of abstract types (Sequence, Mapping).
    Abstract types cannot be subtypes of concrete types.
    """
    # Import here to avoid circular imports
    from collections import Counter, OrderedDict, defaultdict, deque
    from collections.abc import (Container, Iterable, Mapping, MutableMapping,
                                 MutableSequence, Sequence)
    from typing import Dict, FrozenSet, List, Set, Tuple

    # Define abstraction hierarchy (concrete -> abstract)
    concrete_to_abstract = {
        # Basic types
        list: {List, Sequence, MutableSequence, Iterable, Container},
        dict: {Dict, Mapping, MutableMapping, Container},
        set: {Set, Iterable, Container},
        tuple: {Tuple, Sequence, Iterable, Container},
        frozenset: {FrozenSet, Iterable, Container},
        # Specialized collections
        defaultdict: {
            defaultdict,
            DefaultDict,
            dict,
            Dict,
            Mapping,
            MutableMapping,
            Container,
        },
        Counter: {Counter, dict, Dict, Mapping, MutableMapping, Container},
        OrderedDict: {OrderedDict, dict, Dict, Mapping, MutableMapping, Container},
        deque: {deque, MutableSequence, Sequence, Iterable, Container},
    }

    # Check if sub_origin can be a subtype of super_origin
    if sub_origin in concrete_to_abstract:
        return super_origin in concrete_to_abstract[sub_origin]

    # If sub_origin not in mapping, check if they're the same
    return sub_origin == super_origin


def _is_covariant_arg(sub_arg: Type[Any], super_arg: Type[Any]) -> bool:
    """
    Check if sub_arg is covariant with super_arg.

    For most containers, we assume covariance: Container[Derived] <: Container[Base]
    """
    # Handle Any type
    if super_arg is Any:
        return True
    if sub_arg is Any:
        return False  # Any is not a subtype of specific types

    # Recursive check for nested generics
    return extended_issubclass(sub_arg, super_arg)


def _check_runtime_origin_compatibility(
    obj_type: Type[Any], target_origin: Type[Any]
) -> bool:
    """Check if object type is compatible with target origin at runtime."""
    # Use our equivalence system
    if is_equivalent_origin(obj_type, target_origin):
        return True

    # Fallback to regular isinstance check for concrete types
    try:
        if inspect.isclass(target_origin):
            # Create a dummy instance to test (avoid side effects)
            return obj_type == target_origin or issubclass(obj_type, target_origin)
    except (TypeError, AttributeError):
        pass

    return False


def _validate_generic_args(obj: Any, args: tuple, origin: Type[Any]) -> bool:
    """
    Validate that object's contents match the generic type arguments.

    This performs runtime validation of generic types by checking elements.
    """
    try:
        # Handle different container types
        if origin in (list, tuple) or is_equivalent_origin(origin, list):
            return _validate_sequence_args(obj, args)
        elif origin == dict or is_equivalent_origin(origin, dict):
            return _validate_mapping_args(obj, args)
        elif origin in (set, frozenset) or is_equivalent_origin(origin, set):
            return _validate_set_args(obj, args)
        else:
            # For unknown types, just check if it's the right container type
            return True
    except (TypeError, AttributeError):
        return False


def _validate_sequence_args(obj: Any, args: tuple) -> bool:
    """Validate sequence type arguments."""
    if not args:
        return True

    element_type = args[0]

    # Empty containers are valid for any element type
    if not obj:
        return True

    # Special case for Any type
    if element_type is Any:
        return True

    # Check a sample of elements (for performance)
    sample_size = min(10, len(obj)) if hasattr(obj, "__len__") else 10
    count = 0

    for item in obj:
        if count >= sample_size:
            break
        if not extended_isinstance(item, element_type):
            return False
        count += 1

    return True


def _validate_mapping_args(obj: Any, args: tuple) -> bool:
    """Validate mapping type arguments."""
    if len(args) < 2:
        return True

    key_type, value_type = args[0], args[1]

    # Empty containers are valid for any key/value types
    if not obj:
        return True

    # Special case for Any types
    if key_type is Any and value_type is Any:
        return True

    # Check a sample of key-value pairs
    sample_size = min(10, len(obj)) if hasattr(obj, "__len__") else 10
    count = 0

    for key, value in obj.items():
        if count >= sample_size:
            break

        key_valid = key_type is Any or extended_isinstance(key, key_type)
        value_valid = value_type is Any or extended_isinstance(value, value_type)

        if not (key_valid and value_valid):
            return False
        count += 1

    return True


def _validate_set_args(obj: Any, args: tuple) -> bool:
    """Validate set type arguments."""
    if not args:
        return True

    element_type = args[0]

    # Empty containers are valid for any element type
    if not obj:
        return True

    # Special case for Any type
    if element_type is Any:
        return True

    # Check a sample of elements
    sample_size = min(10, len(obj)) if hasattr(obj, "__len__") else 10
    count = 0

    for item in obj:
        if count >= sample_size:
            break
        if not extended_isinstance(item, element_type):
            return False
        count += 1

    return True
