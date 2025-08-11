"""
Typemapping package - Advanced type compatibility and checking system.

This package provides sophisticated type checking capabilities that go beyond
Python's built-in isinstance and issubclass, supporting:

- Generic type compatibility (List[int] ~ Sequence[int])
- Collection specializations (Counter ~ dict, OrderedDict ~ dict)
- Runtime type validation with sampling
- Cross-version compatibility (typing vs collections vs typing_extensions)
- Variance handling (covariance, contravariance)
- Union and Optional type support
- Python 3.8+ compatibility layer for Annotated types

Usage:
    from typemapping.origins import is_equivalent_origin, get_equivalent_origin
    from typemapping.type_check import extended_isinstance, generic_issubclass
    from typemapping.compat import get_args, get_origin  # Python 3.8+ compatible
"""

__version__ = "1.0.0"

__all__ = [
    # types mapping
    "VarTypeInfo",
    "get_field_type",
    "get_func_args",
    "is_Annotated",
    "map_dataclass_fields",
    "map_func_args",
    "map_model_fields",
    "map_init_field",
    "map_return_type",
    "get_return_type",
    "NO_DEFAULT",
    "get_safe_type_hints",
    "defensive_issubclass",
    "is_equal_type",
    "unwrap_partial",
    # Core origin functions
    "is_equivalent_origin",
    "get_equivalent_origin",
    "are_args_compatible",
    "is_fully_compatible",
    "get_compatibility_chain",
    "debug_type_info",
    # Extended type checking
    "extended_isinstance",
    "generic_issubclass",
    "is_equal_type",
    "is_Annotated",
    "defensive_issubclass",
    # Compatibility layer (Python 3.8+)
    "get_args",
    "get_origin",
    "is_annotated_type",
    "strip_annotated",
    "get_annotated_metadata",
    "extend_equiv_otigin",
    "is_optional_type",
    "get_optional_inner_type",
    "get_nested_field_type"
]


from typemapping.typemapping import (
    get_nested_field_type,
    NO_DEFAULT,
    VarTypeInfo,
    get_field_type,
    get_func_args,
    get_return_type,
    get_safe_type_hints,
    map_dataclass_fields,
    map_func_args,
    map_init_field,
    map_model_fields,
    map_return_type,
    unwrap_partial,
)

# Re-export compatibility functions
from .compat import (
    get_annotated_metadata,
    get_args,
    get_origin,
    is_annotated_type,
    strip_annotated,
)

# Re-export main functionality
from .origins import (
    are_args_compatible,
    debug_type_info,
    extend_equiv_otigin,
    get_compatibility_chain,
    get_equivalent_origin,
    is_equivalent_origin,
    is_fully_compatible,
)
from .type_check import (
    defensive_issubclass,
    extended_isinstance,
    generic_issubclass,
    get_optional_inner_type,
    is_equal_type,
    is_optional_type,
)
