"""
Complete type checking module that provides extended type validation capabilities.

This module offers advanced type checking that goes beyond Python's built-in isinstance
and issubclass, supporting generic types, variance, and runtime validation.
"""

import inspect
import typing
from typing import Any, DefaultDict, Type, Union, get_args, get_origin, Optional
from collections import deque, defaultdict

# Import both typing and collections versions to handle conflicts
try:
    from collections import Counter as CollectionsCounter
    from collections import OrderedDict as CollectionsOrderedDict  
    from collections import ChainMap as CollectionsChainMap
except ImportError:
    CollectionsCounter = None
    CollectionsOrderedDict = None
    CollectionsChainMap = None

# Import typing versions
try:
    from typing import Counter as TypingCounter
    from typing import OrderedDict as TypingOrderedDict
    from typing import ChainMap as TypingChainMap
except ImportError:
    TypingCounter = None
    TypingOrderedDict = None
    TypingChainMap = None

from typemapping.origins import is_equivalent_origin

# Handle Annotated imports for compatibility across Python versions
try:
    import typing_extensions
    typing_extensions_Annotated = getattr(typing_extensions, 'Annotated', None)
except ImportError:
    typing_extensions_Annotated = None

# Python 3.9+ has Annotated in typing
typing_Annotated = getattr(typing, 'Annotated', None)


# ===== PUBLIC API FUNCTIONS =====

def extended_issubclass(subtype: Type[Any], supertype: Type[Any]) -> bool:
    """
    Extended issubclass that works with generic types and handles variance.

    This function provides sophisticated type relationship checking that supports:
    - Covariance: Container[Derived] is subclass of Container[Base] 
    - Abstraction: Concrete types are subclasses of abstract equivalents
    - Generic types: Full support for parameterized types
    - Union types: Proper handling of Union type relationships
    - Optional types: Support for Optional[T] relationships

    Rules:
    - Container[Derived] <: Container[Base] if Derived <: Base (covariance)
    - Concrete types <: abstract equivalents (List[T] <: Sequence[T])
    - Abstract types NOT <: concrete types (Sequence[T] not <: List[T])
    - Union[A, B] <: C if A <: C and B <: C
    - T <: Union[A, B] if T <: A or T <: B

    Args:
        subtype: Type to check if it's a subclass
        supertype: Type to check against

    Returns:
        True if subtype is a subclass of supertype

    Examples:
        >>> extended_issubclass(List[Derived], Sequence[Base])  # True - covariance + abstraction
        >>> extended_issubclass(List[Base], Sequence[Derived])  # False - contravariance
        >>> extended_issubclass(List[Base], Sequence[Base])     # True - abstraction
        >>> extended_issubclass(Sequence[Base], List[Base])     # False - concrete from abstract
        >>> extended_issubclass(Union[List[int], Set[int]], Iterable[int])  # True
    """
    # Handle Union types
    if _is_union_type(supertype):
        # subtype <: Union[A, B] if subtype <: A or subtype <: B
        return any(extended_issubclass(subtype, arg) for arg in get_args(supertype))

    if _is_union_type(subtype):
        # Union[A, B] <: supertype if A <: supertype and B <: supertype
        return all(extended_issubclass(arg, supertype) for arg in get_args(subtype))

    # Get origins and args
    sub_origin = get_origin(subtype) or subtype
    super_origin = get_origin(supertype) or supertype
    sub_args = get_args(subtype)
    super_args = get_args(supertype)

    # Handle Optional types (Union[T, None])
    if _is_optional_type(supertype):
        super_inner = _get_optional_inner_type(supertype)
        if _is_optional_type(subtype):
            sub_inner = _get_optional_inner_type(subtype)
            return extended_issubclass(sub_inner, super_inner)
        else:
            # T <: Optional[U] if T <: U
            return extended_issubclass(subtype, super_inner)

    if _is_optional_type(subtype):
        # Optional[T] <: U only if both T <: U and None <: U
        # Since None is not a subtype of most types, this is usually False
        # Unless U is also Optional or a Union containing None
        if _is_optional_type(supertype) or _is_union_type(supertype):
            return any(extended_issubclass(subtype, arg) for arg in get_args(supertype))
        return False

    # Check origin compatibility using our equivalence system
    if not _is_subtype_origin(sub_origin, super_origin):
        return False

    # If no generic arguments, we're done
    if not sub_args and not super_args:
        return True

    # If one has args and other doesn't, they're not compatible
    if bool(sub_args) != bool(super_args):
        return False

    # Both must have same number of type arguments
    if len(sub_args) != len(super_args):
        return False

    # Check covariance of type arguments
    return all(
        _is_covariant_arg(sub_arg, super_arg)
        for sub_arg, super_arg in zip(sub_args, super_args)
    )


def extended_isinstance(obj: Any, type_hint: Type[Any]) -> bool:
    """
    Extended isinstance that works with generic types and runtime type checking.

    This function performs runtime type validation for generic types by actually
    checking the contents of containers. It supports sampling for performance
    on large containers and handles complex nested generic types.

    Features:
    - Runtime validation of generic type arguments
    - Performance optimization via sampling for large containers
    - Support for Union and Optional types
    - Nested generic type validation
    - Container type compatibility checking

    Args:
        obj: Object to check
        type_hint: Type to check against (can be generic)

    Returns:
        True if obj is an instance of type_hint

    Examples:
        >>> extended_isinstance([1, 2, 3], List[int])  # True
        >>> extended_isinstance([1, 2, 3], Sequence[int])  # True
        >>> extended_isinstance([1, 2, 3], Sequence[str])  # False
        >>> extended_isinstance([1, 2, 3], Set[int])  # False
        >>> extended_isinstance({'a': 1}, Dict[str, int])  # True
        >>> extended_isinstance(None, Optional[int])  # True
    """
    # Handle Union types
    if _is_union_type(type_hint):
        return any(extended_isinstance(obj, arg) for arg in get_args(type_hint))

    # Handle Optional types
    if _is_optional_type(type_hint):
        if obj is None:
            return True
        inner_type = _get_optional_inner_type(type_hint)
        return extended_isinstance(obj, inner_type)

    # Get the origin type and args
    origin = get_origin(type_hint) or type_hint
    args = get_args(type_hint)

    # Check basic type compatibility using our equivalence system
    obj_type = type(obj)
    if not _check_runtime_origin_compatibility(obj_type, origin):
        return False

    # If no generic arguments, basic isinstance is enough
    if not args:
        return True

    # Runtime validation of generic arguments
    return _validate_generic_args(obj, args, origin)


def is_Annotated(bt: Optional[Type[Any]]) -> bool:
    """
    Check if type is Annotated, handling None case and version compatibility.
    
    This function detects Annotated types from both typing and typing_extensions
    modules, providing compatibility across different Python versions.

    Args:
        bt: Type to check (can be None)

    Returns:
        True if type is Annotated[T, ...], False otherwise

    Examples:
        >>> from typing import Annotated
        >>> is_Annotated(Annotated[int, "positive"])  # True
        >>> is_Annotated(int)  # False
        >>> is_Annotated(None)  # False
    """
    if bt is None:
        return False
    
    origin = get_origin(bt)
    
    # Check against both typing and typing_extensions versions
    annotated_types = []
    if typing_Annotated is not None:
        annotated_types.append(typing_Annotated)
    if typing_extensions_Annotated is not None:
        annotated_types.append(typing_extensions_Annotated)
    
    return origin in annotated_types


def is_equal_type(t1: Type[Any], t2: Type[Any]) -> bool:
    """
    Compare two types for strict equality, handling both basic and generic types.
    
    This function performs exact type equality checking with no variance allowed.
    Unlike extended_issubclass which allows covariance, this requires exact matches
    for all type parameters.

    Args:
        t1: First type to compare
        t2: Second type to compare

    Returns:
        True if types are exactly equal, False otherwise

    Examples:
        >>> is_equal_type(List[int], List[int])  # True
        >>> is_equal_type(List[int], Sequence[int])  # False (different origins)
        >>> is_equal_type(List[int], List[str])  # False (different args)
        >>> is_equal_type(int, int)  # True
        >>> is_equal_type(None, None)  # True
    """
    # Handle None cases
    if t1 is None or t2 is None:
        return t1 is t2

    # Get origins and args
    origin1, origin2 = get_origin(t1), get_origin(t2)
    args1, args2 = get_args(t1), get_args(t2)

    # If both have no origin (basic types like str, int), compare directly
    if origin1 is None and origin2 is None:
        return t1 is t2

    # If one has origin and other doesn't, they're different
    if (origin1 is None) != (origin2 is None):
        return False

    # Both have origins, compare origins and args recursively
    if origin1 != origin2:
        return False
    
    if len(args1) != len(args2):
        return False
    
    # Recursively check all arguments for strict equality
    return all(is_equal_type(arg1, arg2) for arg1, arg2 in zip(args1, args2))


def safe_issubclass(cls: Any, classinfo: Type[Any]) -> bool:
    """
    Safe version of issubclass that handles edge cases and provides conservative Union handling.
    
    This function provides a safe wrapper around issubclass with comprehensive error
    handling and conservative semantics for Union types. Unlike extended_issubclass,
    this requires ALL union members to be subclasses (not just ANY).

    Features:
    - Comprehensive error handling (TypeError, AttributeError, RecursionError)
    - Conservative Union handling (ALL members must be subclasses)
    - Safe handling of None and malformed types
    - Generic type origin extraction

    Args:
        cls: Type to check if it's a subclass (can be None or malformed)
        classinfo: Type to check against

    Returns:
        True if cls is safely determined to be a subclass of classinfo

    Examples:
        >>> safe_issubclass(list, Sequence)  # True
        >>> safe_issubclass(Union[list, tuple], Sequence)  # True (both are subclasses)
        >>> safe_issubclass(Union[list, str], Sequence)  # False (str is not)
        >>> safe_issubclass(None, int)  # False (safe handling)
        >>> safe_issubclass("invalid", int)  # False (safe handling)
    """
    if cls is None:
        return False

    try:
        # Handle Union types - check if ALL types in union are subclasses
        # This is more restrictive but more logical
        if get_origin(cls) is Union:
            union_args = get_args(cls)
            return all(safe_issubclass(arg, classinfo) for arg in union_args)

        # Handle Generic types - get the origin class
        origin_cls = get_origin(cls)
        if origin_cls is not None:
            cls = origin_cls

        # Only call issubclass if cls is actually a class
        if inspect.isclass(cls):
            return issubclass(cls, classinfo)
        return False
    except (TypeError, AttributeError, RecursionError):
        return False


# ===== PRIVATE HELPER FUNCTIONS =====

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
    
    # Map specializations to their base types
    specialization_map = {}
    
    # Add concrete collections if available
    if CollectionsCounter:
        specialization_map[CollectionsCounter] = dict
    if CollectionsOrderedDict:
        specialization_map[CollectionsOrderedDict] = dict
    if CollectionsChainMap:
        specialization_map[CollectionsChainMap] = dict
    
    # Add typing collections if available  
    if TypingCounter:
        specialization_map[TypingCounter] = dict
    if TypingOrderedDict:
        specialization_map[TypingOrderedDict] = dict
    if TypingChainMap:
        specialization_map[TypingChainMap] = dict
    
    # Add defaultdict and deque (these are always available)
    specialization_map[defaultdict] = dict
    specialization_map[deque] = list  # deque behaves like a list

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
        # Basic specialized collections
        defaultdict: {defaultdict, DefaultDict, dict, Dict, Mapping, MutableMapping, Container},
        deque: {deque, MutableSequence, Sequence, Iterable, Container},
    }
    
    # Add concrete collections if available
    if CollectionsCounter:
        concrete_to_abstract[CollectionsCounter] = {CollectionsCounter, dict, Dict, Mapping, MutableMapping, Container}
    if CollectionsOrderedDict:
        concrete_to_abstract[CollectionsOrderedDict] = {CollectionsOrderedDict, dict, Dict, Mapping, MutableMapping, Container}
    if CollectionsChainMap:
        concrete_to_abstract[CollectionsChainMap] = {CollectionsChainMap, Mapping, MutableMapping, Container}
    
    # Add typing collections if available
    if TypingCounter:
        concrete_to_abstract[TypingCounter] = {TypingCounter, dict, Dict, Mapping, MutableMapping, Container}
    if TypingOrderedDict:
        concrete_to_abstract[TypingOrderedDict] = {TypingOrderedDict, dict, Dict, Mapping, MutableMapping, Container}
    if TypingChainMap:
        concrete_to_abstract[TypingChainMap] = {TypingChainMap, Mapping, MutableMapping, Container}

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


# ===== PUBLIC API SUMMARY =====
"""
PUBLIC API FUNCTIONS:

Type Relationship Checking:
- extended_issubclass(subtype, supertype) -> bool
  Advanced subclass checking with variance and generic support
  
- safe_issubclass(cls, classinfo) -> bool  
  Conservative subclass checking with error handling

Runtime Type Validation:
- extended_isinstance(obj, type_hint) -> bool
  Runtime validation of generic types with sampling

Type Equality and Introspection:
- is_equal_type(t1, t2) -> bool
  Strict type equality with no variance
  
- is_Annotated(bt) -> bool
  Check if type is Annotated[T, ...]

All functions handle:
- Generic types (List[int], Dict[str, float])
- Union types (Union[str, int]) 
- Optional types (Optional[int])
- Complex nested types (List[Dict[str, Optional[int]]])
- Collections specializations (defaultdict, Counter, etc.)
- Error cases (None, malformed types)
"""