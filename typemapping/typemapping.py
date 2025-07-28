"""
Type mapping and introspection utilities for frameworks like FastAPI, SQLAlchemy, Pydantic.

This module provides sophisticated type inspection capabilities for extracting type information
from function arguments, class fields, and annotations. It supports:

- Function argument mapping with type hints
- Dataclass field inspection
- Class field mapping from type hints
- Annotated type unwrapping and metadata extraction
- Partial function handling
- Safe type hint resolution with forward references

Integrates with the advanced type checking system from typemapping.origins and typemapping.type_check.
"""

import inspect
import sys
from dataclasses import MISSING, dataclass, fields
from functools import lru_cache, partial
from inspect import Parameter, signature
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    get_type_hints,
)

# Import our compatibility layer
from typemapping.compat import (
    get_annotated_metadata,
    get_args,
    get_origin,
    strip_annotated,
)

# Import our advanced type checking functions
from typemapping.type_check import (
    extended_isinstance,
    generic_issubclass,
    is_Annotated,
    is_equal_type,
)

# Python 3.8 compatibility - Field is not subscriptable
if sys.version_info >= (3, 9):
    from dataclasses import Field
else:
    from dataclasses import Field as _Field

    Field = _Field  # type: ignore

T = TypeVar("T")


@dataclass
class VarTypeInfo:
    """
    Comprehensive type information for function arguments or class fields.

    This class encapsulates all type-related information including the original
    annotation, resolved base type, default values, and metadata from Annotated types.
    """

    name: str
    argtype: Optional[Type[Any]]  # Original type annotation
    basetype: Optional[Type[Any]]  # Resolved type (unwrapped from Annotated)
    default: Optional[Any]
    has_default: bool = False
    extras: Optional[Tuple[Any, ...]] = None  # Metadata from Annotated[T, ...]

    @property
    def origin(self) -> Optional[Type[Any]]:
        """Get the origin of the base type (e.g., list from List[int])."""
        return get_origin(self.basetype)

    @property
    def args(self) -> Tuple[Any, ...]:
        """Get the type arguments (e.g., (int,) from List[int])."""
        return get_args(self.basetype) if self.basetype is not None else ()

    def isequal(self, arg: Any) -> bool:
        """
        Check if this type info equals another type using advanced type equality.

        Uses our enhanced is_equal_type for precise comparison.
        """
        if arg is None or self.basetype is None:
            return arg == self.basetype

        if is_Annotated(arg):
            return self.isequal(get_args(arg)[0])

        return is_equal_type(self.basetype, arg)

    def istype(self, tgttype: type) -> bool:
        """
        Check if this type info is compatible with target type.

        Uses our advanced type checking system for sophisticated compatibility.
        """
        if tgttype is None or self.basetype is None:
            return False

        if is_Annotated(tgttype):
            # For Python 3.8 compatibility, we need to handle this carefully
            args = get_args(tgttype)
            if args:
                return self.istype(args[0])
            return False

        try:
            # Use our advanced generic_issubclass for better type relationships
            return self.isequal(tgttype) or generic_issubclass(self.basetype, tgttype)
        except (TypeError, AttributeError):
            return False

    def isinstance_check(self, obj: Any) -> bool:
        """
        Check if object is instance of this type using extended isinstance.

        This provides runtime type validation with support for generics.
        """
        if self.basetype is None:
            return obj is None

        try:
            return extended_isinstance(obj, self.basetype)
        except (TypeError, AttributeError):
            return False

    def getinstance(self, tgttype: Type[T], default: bool = True) -> Optional[T]:
        """
        Get instance of target type from extras or default.

        This is useful for extracting framework-specific objects from Annotated metadata.
        """
        if not isinstance(tgttype, type):
            return None

        # Search in Annotated metadata
        if self.extras is not None:
            founds = [e for e in self.extras if isinstance(e, tgttype)]
            if len(founds) > 0:
                return founds[0]

        # Check default value
        if default and self.has_default and isinstance(self.default, tgttype):
            return self.default

        return None

    def hasinstance(self, tgttype: type, default: bool = True) -> bool:
        """Check if has instance of target type."""
        return self.getinstance(tgttype, default) is not None

    def get_all_instances(self, tgttype: Type[T]) -> List[T]:
        """Get all instances of target type from extras and default."""
        instances = []

        # From extras
        if self.extras is not None:
            instances.extend([e for e in self.extras if isinstance(e, tgttype)])

        # From default
        if self.has_default and isinstance(self.default, tgttype):
            instances.append(self.default)

        return instances


class _NoDefault:
    """Sentinel object for parameters with no default value."""

    def __repr__(self) -> str:
        return "NO_DEFAULT"

    def __str__(self) -> str:
        return "NO_DEFAULT"


NO_DEFAULT = _NoDefault()


@lru_cache(maxsize=256)
def _get_module_globals(module_name: str) -> Dict[str, Any]:
    """Get module globals with caching for type hint resolution."""
    try:
        return vars(sys.modules[module_name]).copy()
    except KeyError:
        return {}


def get_safe_type_hints(
    obj: Any, localns: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Get type hints safely, handling ForwardRef and Self references.

    This function provides robust type hint extraction that handles:
    - Forward references (strings)
    - Self references in class methods
    - Nested classes
    - Module-level type resolution
    """
    try:
        if inspect.isclass(obj):
            cls: Optional[Any] = obj
        elif inspect.isfunction(obj) or inspect.ismethod(obj):
            # Handle nested classes and methods
            qualname_parts = obj.__qualname__.split(".")
            cls = obj
            for part in qualname_parts[:-1]:
                try:
                    cls = getattr(sys.modules[obj.__module__], part, None)
                    if cls is None:
                        break
                except (AttributeError, KeyError):
                    cls = None
                    break
        else:
            cls = None

        globalns = _get_module_globals(obj.__module__)

        # Add the class to global namespace for self-references
        if cls and inspect.isclass(cls):
            globalns[cls.__name__] = cls
            # Handle nested classes
            if "." in obj.__qualname__:
                parts = obj.__qualname__.split(".")
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:
                        break
                    try:
                        nested_cls = getattr(sys.modules[obj.__module__], part, None)
                        if nested_cls and inspect.isclass(nested_cls):
                            globalns[part] = nested_cls
                    except (AttributeError, KeyError):
                        pass

        # Add localns to globalns if provided
        if localns:
            globalns.update(localns)

        # For Python 3.8, we need to handle None type specially
        if sys.version_info < (3, 9):
            globalns["NoneType"] = type(None)

        return get_type_hints(
            obj, globalns=globalns, localns=localns, include_extras=True
        )
    except (NameError, AttributeError, TypeError, RecursionError):
        # Fallback to basic inspection if type hints fail
        try:
            if hasattr(obj, "__annotations__"):
                annotations = obj.__annotations__.copy()
                # In Python 3.8, forward refs remain as strings in fallback
                return annotations
        except AttributeError:
            pass
        return {}


def resolve_class_default(param: Parameter) -> Tuple[bool, Any]:
    """Resolve default value for class parameter."""
    if param.default is not Parameter.empty:
        return True, param.default
    return False, NO_DEFAULT


def resolve_dataclass_default(
    field: Any,
) -> Tuple[bool, Any]:  # Python 3.8 compat - can't use Field[Any]
    """Resolve default value for dataclass field."""
    if field.default is not MISSING:
        return True, field.default
    elif field.default_factory is not MISSING:
        # For dataclass fields, we return the factory itself for consistency
        # The caller should decide when to call it
        try:
            # Try to call factory for simple cases
            if callable(field.default_factory):
                factory_result = field.default_factory()
                return True, factory_result
        except Exception:
            # If factory fails, return the factory itself
            pass
        return True, field.default_factory
    return False, NO_DEFAULT


def field_factory(
    obj: Union[Any, Parameter],  # Python 3.8 compat - can't use Field[Any]
    hint: Any,
    bt_default_fallback: bool = True,
) -> VarTypeInfo:
    """
    Create VarTypeInfo from field or parameter.

    This is the core function that extracts comprehensive type information
    from function parameters or dataclass fields.
    """
    resolve_default = (
        resolve_class_default
        if isinstance(obj, Parameter)
        else resolve_dataclass_default
    )

    has_default, default = resolve_default(obj)  # type: ignore

    if hint is not inspect._empty and hint is not None:
        argtype = hint
    elif bt_default_fallback and default not in (NO_DEFAULT, None):
        argtype = type(default)
    else:
        argtype = None

    return make_funcarg(
        name=obj.name,
        tgttype=argtype,
        annotation=hint,
        default=default,
        has_default=has_default,
    )


def make_funcarg(
    name: str,
    tgttype: Optional[Type[Any]],
    annotation: Optional[Type[Any]] = None,
    default: Any = None,
    has_default: bool = False,
) -> VarTypeInfo:
    """
    Create VarTypeInfo with proper handling of Annotated types.

    This function unwraps Annotated types and extracts metadata for framework use.
    """
    basetype = tgttype
    extras = None

    if annotation is not None and is_Annotated(annotation):
        # Use our compat layer for Python 3.8 support
        basetype = strip_annotated(annotation)
        metadata = get_annotated_metadata(annotation)
        if metadata:
            extras = metadata

    return VarTypeInfo(
        name=name,
        argtype=tgttype,
        basetype=basetype,
        default=default,
        extras=extras,
        has_default=has_default,
    )


def unwrap_partial(
    func: Callable[..., Any],
) -> Tuple[Callable[..., Any], List[Any], Dict[str, Any]]:
    """
    Recursively unwrap partial functions.

    This handles nested partials correctly, preserving argument order and precedence.
    """
    partial_kwargs: Dict[Any, Any] = {}
    partial_args: List[Any] = []

    # Handle nested partials
    while isinstance(func, partial):
        # Merge keywords, with inner partials taking precedence
        new_kwargs = func.keywords or {}
        for k, v in partial_kwargs.items():
            if k not in new_kwargs:
                new_kwargs[k] = v
        partial_kwargs = new_kwargs

        # Prepend args from this partial
        partial_args = list(func.args or []) + partial_args
        func = func.func

    return func, partial_args, partial_kwargs


# ===== FIELD MAPPING STRATEGIES =====


def map_init_field(
    cls: type,
    bt_default_fallback: bool = True,
    localns: Optional[Dict[str, Any]] = None,
) -> List[VarTypeInfo]:
    """
    Map fields from __init__ method.

    This strategy extracts type information from constructor parameters.
    """
    init_method = cls.__init__

    # If it's object.__init__, return empty list since it has no useful parameters
    if init_method is object.__init__:
        return []

    hints = get_safe_type_hints(init_method, localns)
    sig = signature(init_method)
    items = [(name, param) for name, param in sig.parameters.items() if name != "self"]

    return [
        field_factory(obj, hints.get(name), bt_default_fallback) for name, obj in items
    ]


def map_dataclass_fields(
    cls: type,
    bt_default_fallback: bool = True,
    localns: Optional[Dict[str, Any]] = None,
) -> List[VarTypeInfo]:
    """
    Map dataclass fields.

    This strategy extracts type information from dataclass field definitions.
    """
    hints = get_safe_type_hints(cls, localns)
    items = [(field.name, field) for field in fields(cls)]

    return [
        field_factory(obj, hints.get(name), bt_default_fallback) for name, obj in items
    ]


def map_model_fields(
    cls: type,
    bt_default_fallback: bool = True,
    localns: Optional[Dict[str, Any]] = None,
) -> List[VarTypeInfo]:
    """
    Map model fields from type hints and class attributes.

    This strategy works with any class that has type hints, useful for
    model classes, configuration classes, etc.
    """
    hints = get_safe_type_hints(cls, localns)
    items = []

    for name in hints:
        # Skip methods and properties that might have side effects
        attr = None
        try:
            # Use getattr carefully to avoid triggering descriptors
            if hasattr(cls, name):
                attr_descriptor = getattr(type(cls), name, None)
                if isinstance(attr_descriptor, property):
                    # Skip properties to avoid side effects
                    attr = Parameter.empty
                elif callable(getattr(cls, name, None)):
                    # Skip methods
                    attr = Parameter.empty
                else:
                    attr = getattr(cls, name, Parameter.empty)
            else:
                attr = Parameter.empty
        except (AttributeError, TypeError):
            attr = Parameter.empty

        param = Parameter(
            name,
            Parameter.POSITIONAL_OR_KEYWORD,
            default=attr,
        )
        items.append((name, param))

    return [
        field_factory(obj, hints.get(name), bt_default_fallback) for name, obj in items
    ]


# ===== FUNCTION MAPPING UTILITIES =====


def map_return_type(
    func: Callable[..., Any], localns: Optional[Dict[str, Any]] = None
) -> VarTypeInfo:
    """Map function return type."""
    sig = inspect.signature(func)
    hints = get_safe_type_hints(func, localns)
    raw_return_type = hints.get("return", sig.return_annotation)

    if raw_return_type is inspect.Signature.empty:
        raw_return_type = None

    # Handle special case for None return type
    if raw_return_type is None and "return" in hints:
        # Check if the annotation was explicitly None (not just missing)
        func_annotations = getattr(func, "__annotations__", {})
        if "return" in func_annotations and func_annotations["return"] is None:
            raw_return_type = type(None)

    return make_funcarg(
        name=func.__name__,
        tgttype=raw_return_type,
        annotation=raw_return_type,
    )


def get_return_type(func: Callable[..., Any]) -> Optional[Type[Any]]:
    """Get function return type."""
    returntype = map_return_type(func)
    return returntype.basetype


def map_func_args(
    func: Callable[..., Any],
    localns: Optional[Dict[str, Any]] = None,
    bt_default_fallback: bool = True,
) -> Tuple[Sequence[VarTypeInfo], VarTypeInfo]:
    """Map function arguments and return type."""
    funcargs = get_func_args(func, localns, bt_default_fallback)
    return_type = map_return_type(func, localns)
    return funcargs, return_type


def get_func_args(
    func: Callable[..., Any],
    localns: Optional[Dict[str, Any]] = None,
    bt_default_fallback: bool = True,
) -> Sequence[VarTypeInfo]:
    """
    Get function arguments as VarTypeInfo list.

    This function handles partial functions, type hints, and default values
    to provide comprehensive argument information.
    """
    # Handle partial functions
    original_func, partial_args, partial_kwargs = unwrap_partial(func)

    sig = inspect.signature(original_func)
    hints = get_safe_type_hints(original_func, localns)

    funcargs: List[VarTypeInfo] = []

    # Skip parameters that are filled by partial args
    skip_count = len(partial_args)

    for i, (name, param) in enumerate(sig.parameters.items()):
        # Skip parameters filled by positional partial args
        if i < skip_count:
            continue

        # Skip parameters filled by partial kwargs
        if name in partial_kwargs:
            continue

        # Skip *args and **kwargs
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue

        annotation = hints.get(name, param.annotation)
        arg = field_factory(param, annotation, bt_default_fallback)
        funcargs.append(arg)

    return funcargs


# ===== FIELD TYPE UTILITIES =====


def get_field_type_(
    tgt: Type[Any],
    fieldname: str,
    localns: Optional[Dict[str, Any]] = None,
) -> Optional[Type[Any]]:
    """
    Get field type from various sources.

    This function tries multiple strategies to find type information:
    1. Class-level type hints
    2. __init__ method type hints
    3. Property return type hints
    4. Method return type hints
    """
    # Try class-level type hints first
    try:
        cls_th = get_safe_type_hints(tgt, localns)
        if fieldname in cls_th:
            return cls_th[fieldname]
    except (TypeError, AttributeError):
        pass

    # Try __init__ method type hints
    try:
        init_method = getattr(tgt, "__init__", None)
        if init_method and init_method is not object.__init__:
            init_th = get_safe_type_hints(init_method, localns)
            if fieldname in init_th:
                return init_th[fieldname]
    except (TypeError, AttributeError):
        pass

    # Try to get attribute and infer type
    try:
        attr = getattr(tgt, fieldname, None)
        if attr is None:
            return None

        # Handle properties
        if isinstance(attr, property):
            try:
                if attr.fget:
                    prop_th = get_safe_type_hints(attr.fget, localns)
                    if "return" in prop_th:
                        return prop_th["return"]
            except (TypeError, AttributeError):
                pass

        # Handle regular methods
        elif callable(attr) and hasattr(attr, "__annotations__"):
            try:
                method_th = get_safe_type_hints(attr, localns)
                if "return" in method_th:
                    return method_th["return"]
            except (TypeError, AttributeError):
                pass

    except (TypeError, AttributeError):
        pass

    return None


def get_field_type(
    tgt: Type[Any],
    fieldname: str,
    localns: Optional[Dict[str, Any]] = None,
) -> Optional[Type[Any]]:
    """Get field type, unwrapping Annotated if present."""
    btype = get_field_type_(tgt, fieldname, localns)
    if btype is not None and is_Annotated(btype):
        # Use our compat layer for Python 3.8 support
        btype = strip_annotated(btype)
    return btype


# ===== CONVENIENCE FUNCTIONS FOR FRAMEWORK INTEGRATION =====


def extract_metadata(var_info: VarTypeInfo, target_type: Type[T]) -> List[T]:
    """
    Extract all metadata instances of target type from VarTypeInfo.

    Useful for framework-specific annotations like FastAPI dependencies,
    SQLAlchemy column definitions, etc.
    """
    return var_info.get_all_instances(target_type)


def has_metadata(var_info: VarTypeInfo, target_type: Type[Any]) -> bool:
    """Check if VarTypeInfo has metadata of specific type."""
    return var_info.hasinstance(target_type)


def get_first_metadata(var_info: VarTypeInfo, target_type: Type[T]) -> Optional[T]:
    """Get first metadata instance of target type."""
    return var_info.getinstance(target_type)


def filter_fields_by_metadata(
    fields: List[VarTypeInfo], target_type: Type[Any]
) -> List[VarTypeInfo]:
    """Filter fields that have specific metadata type."""
    return [field for field in fields if has_metadata(field, target_type)]


def group_fields_by_type(
    fields: List[VarTypeInfo],
) -> Dict[Type[Any], List[VarTypeInfo]]:
    """Group fields by their base type."""
    groups: Dict[Type[Any], List[VarTypeInfo]] = {}
    for field in fields:
        if field.basetype is not None:
            if field.basetype not in groups:
                groups[field.basetype] = []
            groups[field.basetype].append(field)
    return groups
