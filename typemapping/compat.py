"""
Compatibility layer for Python 3.8+ to handle Annotated types correctly.

This module provides wrapper functions around get_origin() and get_args() that
work consistently across Python versions, especially for Annotated types.
"""

import sys
from typing import Any, Tuple, Type, cast
from typing import get_args as typing_get_args
from typing import get_origin as typing_get_origin

# Handle version-specific imports
if sys.version_info >= (3, 9):
    from typing import Annotated as typing_Annotated
    from typing import _AnnotatedAlias  # type: ignore
else:
    typing_Annotated = None  # pragma: no cover
    _AnnotatedAlias = None  # pragma: no cover

try:
    import typing_extensions

    typing_extensions_Annotated = getattr(typing_extensions, "Annotated", None)
    if sys.version_info < (3, 9):  # pragma: no cover
        # In Python 3.8, we need the internal class
        try:
            from typing_extensions import (
                _AnnotatedAlias as typing_extensions_AnnotatedAlias,  # type: ignore
            )
        except ImportError:
            typing_extensions_AnnotatedAlias = None
    else:
        typing_extensions_AnnotatedAlias = None
except ImportError:
    typing_extensions_Annotated = None
    typing_extensions_AnnotatedAlias = None


def _debug_annotated(tp: Type[Any]) -> None:  # pragma: no cover
    """Debug function to inspect Annotated type structure in Python 3.8."""
    pass


def get_origin(tp: Type[Any]) -> Any:
    """
    Get the origin of a type, with proper handling of Annotated types in Python 3.8+.

    This function ensures consistent behavior across Python versions, especially
    for Annotated types from typing_extensions in Python 3.8.
    """
    # First try standard get_origin
    origin = typing_get_origin(tp)
    if origin is not None:
        return origin

    # Special handling for Annotated in Python 3.8
    if sys.version_info < (3, 9):
        # Check if it's a typing_extensions Annotated type
        if hasattr(tp, "__class__"):
            tp_class = tp.__class__
            # Check class name and module
            if (
                tp_class.__name__ in ("_AnnotatedAlias", "AnnotatedMeta")
                and tp_class.__module__ == "typing_extensions"
            ):
                # It's an Annotated type from typing_extensions
                if typing_extensions_Annotated is not None:
                    return typing_extensions_Annotated

        # Also check __origin__ attribute which some types have
        if hasattr(tp, "__origin__"):
            return tp.__origin__

    return None


def get_args(tp: Type[Any]) -> Tuple[Any, ...]:
    """
    Get the arguments of a type, with proper handling of Annotated types in Python 3.8+.

    This function ensures consistent behavior across Python versions, especially
    for Annotated types from typing_extensions in Python 3.8.
    """
    # Special handling for Annotated in Python 3.8 BEFORE trying standard get_args
    if sys.version_info < (3, 9) and is_annotated_type(tp):
        # For typing_extensions._AnnotatedAlias in Python 3.8
        if hasattr(tp, "__origin__") and hasattr(tp, "__metadata__"):
            origin = tp.__origin__
            metadata = tp.__metadata__
            # Ensure metadata is a tuple
            if not isinstance(metadata, tuple):
                metadata = (metadata,)
            return (origin,) + metadata

    # Now try standard get_args
    args = typing_get_args(tp)
    if args:
        # For Annotated types in Python 3.8, typing.get_args only returns the origin
        # We need to check if this is an Annotated type and add metadata
        if sys.version_info < (3, 9) and is_annotated_type(tp) and len(args) == 1:
            # This is likely an Annotated type where get_args only returned the origin
            if hasattr(tp, "__metadata__"):
                metadata = tp.__metadata__
                if not isinstance(metadata, tuple):
                    metadata = (metadata,)
                return args + metadata
        return args

    # Fallback checks for other types
    if hasattr(tp, "__args__"):
        return cast(Tuple[Any], tp.__args__)

    return ()


def is_annotated_type(tp: Type[Any]) -> bool:
    """
    Check if a type is an Annotated type, handling both typing and typing_extensions versions.

    This is more reliable than checking get_origin() == Annotated in Python 3.8.
    """
    if tp is None:
        return False

    # For Python 3.9+, we can use get_origin
    if sys.version_info >= (3, 9):
        origin = get_origin(tp)
        return origin is typing_Annotated or origin is typing_extensions_Annotated

    # For Python 3.8, we need to check more carefully
    if hasattr(tp, "__class__"):
        tp_class = tp.__class__
        # Check for typing_extensions Annotated
        if (
            tp_class.__name__ in ("_AnnotatedAlias", "AnnotatedMeta")
            and tp_class.__module__ == "typing_extensions"
        ):
            return True

    # Also check if it has the expected attributes
    return hasattr(tp, "__metadata__") and hasattr(tp, "__origin__")


def strip_annotated(tp: Type[Any]) -> Type[Any]:
    """
    Strip Annotated wrapper and return the base type.

    If the type is not Annotated, returns it unchanged.
    """
    if is_annotated_type(tp):
        args = get_args(tp)
        if args:
            tp = args[0]
    return cast(Type[Any], tp)


def get_annotated_metadata(tp: Type[Any]) -> Tuple[Any, ...]:
    """
    Get metadata from an Annotated type.

    Returns empty tuple if not an Annotated type or has no metadata.
    """
    if is_annotated_type(tp):
        args = get_args(tp)
        if len(args) > 1:
            return args[1:]

        # Fallback for Python 3.8 - check __metadata__ directly
        if sys.version_info < (3, 9) and hasattr(tp, "__metadata__"):
            metadata = tp.__metadata__
            if isinstance(metadata, tuple):
                return metadata
            else:
                return (metadata,) if metadata is not None else ()

    return ()


# For backward compatibility with existing code
def is_annotated_class(cls: Any) -> bool:
    """
    Check if a class is the Annotated special form itself (not an instance).

    This is used to check if something IS the Annotated type constructor.
    """
    # First check if cls is None to avoid the bug where None is typing_Annotated
    if cls is None:
        return False

    return (
        cls is typing_Annotated
        or cls is typing_extensions_Annotated
        or (
            sys.version_info < (3, 9)
            and cls is not None  # Extra check to be safe
            and hasattr(cls, "__name__")
            and cls.__name__ == "Annotated"
            and hasattr(cls, "__class_getitem__")
        )
    )
