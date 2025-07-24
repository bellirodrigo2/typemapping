import inspect
import sys
from dataclasses import MISSING, Field, dataclass, fields
from functools import lru_cache, partial
from inspect import Parameter, signature

from typing_extensions import Annotated as typing_extensions_Annotated
from typing_extensions import (Any, Callable, Optional, Sequence, Tuple, Type,
                               TypeVar, Union, get_args, get_origin,
                               get_type_hints)

try:
    from typing import Annotated as typing_Annotated
except ImportError:
    typing_Annotated = None

T = TypeVar("T")


def is_Annotated(bt: Optional[Type[Any]]) -> bool:
    """Check if type is Annotated, handling None case"""
    if bt is None:
        return False
    origin = get_origin(bt)
    return origin in (typing_extensions_Annotated, typing_Annotated)


def is_equal_type(t1: Type[Any], t2: Type[Any]) -> bool:
    """Compare two types for equality, handling both basic and generic types"""
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

    # Both have origins, compare origins and args
    return origin1 == origin2 and args1 == args2


def safe_issubclass(cls: Any, classinfo: Type[Any]) -> bool:
    """Safe version of issubclass that handles edge cases"""
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


@dataclass
class VarTypeInfo:
    name: str
    argtype: Optional[Type[Any]]
    basetype: Optional[Type[Any]]
    default: Optional[Any]
    has_default: bool = False
    extras: Optional[tuple[Any, ...]] = None

    @property
    def origin(self) -> Optional[Type[Any]]:
        return get_origin(self.basetype)

    @property
    def args(self) -> tuple[Any, ...]:
        return get_args(self.basetype) if self.basetype is not None else ()

    def isequal(self, arg: Any) -> bool:
        """Check if this type info equals another type"""
        if arg is None or self.basetype is None:
            return arg == self.basetype

        if is_Annotated(arg):
            return self.isequal(get_args(arg)[0])

        if get_origin(arg) is None:
            return self.basetype == arg

        return self.origin == get_origin(arg) and self.args == get_args(arg)

    def istype(self, tgttype: type) -> bool:
        """Check if this type info is compatible with target type"""
        if tgttype is None or self.basetype is None:
            return False

        if is_Annotated(tgttype):
            return self.isequal(get_args(tgttype)[0])

        try:
            return self.isequal(tgttype) or safe_issubclass(self.basetype, tgttype)
        except (TypeError, AttributeError):
            return False

    def getinstance(self, tgttype: Type[T], default: bool = True) -> Optional[T]:
        """Get instance of target type from extras or default"""
        if not isinstance(tgttype, type):
            return None

        if self.extras is not None:
            founds = [e for e in self.extras if isinstance(e, tgttype)]
            if len(founds) > 0:
                return founds[0]

        if default and self.has_default and isinstance(self.default, tgttype):
            return self.default

        return None

    def hasinstance(self, tgttype: type, default: bool = True) -> bool:
        """Check if has instance of target type"""
        return self.getinstance(tgttype, default) is not None


class _NoDefault:
    def __repr__(self) -> str:
        return "NO_DEFAULT"

    def __str__(self) -> str:
        return "NO_DEFAULT"


NO_DEFAULT = _NoDefault()


@lru_cache(maxsize=256)
def _get_module_globals(module_name: str) -> dict[str, Any]:
    """Get module globals with caching"""
    try:
        return vars(sys.modules[module_name]).copy()
    except KeyError:
        return {}


def get_safe_type_hints(
    obj: Any, localns: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """
    Get type hints safely, handling ForwardRef and Self references
    """
    try:
        if inspect.isclass(obj):
            cls = obj
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

        return get_type_hints(
            obj, globalns=globalns, localns=localns, include_extras=True
        )
    except (NameError, AttributeError, TypeError, RecursionError):
        # Fallback to basic inspection if type hints fail
        try:
            if hasattr(obj, "__annotations__"):
                return obj.__annotations__.copy()
        except AttributeError:
            pass
        return {}


def resolve_class_default(param: Parameter) -> tuple[bool, Any]:
    """Resolve default value for class parameter"""
    if param.default is not Parameter.empty:
        return True, param.default
    return False, NO_DEFAULT


def resolve_dataclass_default(field: Field[Any]) -> tuple[bool, Any]:
    """Resolve default value for dataclass field"""
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
    obj: Union[Field[Any], Parameter],
    hint: Any,
    bt_default_fallback: bool = True,
) -> VarTypeInfo:
    """Create VarTypeInfo from field or parameter"""
    resolve_default = (
        resolve_class_default
        if isinstance(obj, Parameter)
        else resolve_dataclass_default
    )

    has_default, default = resolve_default(obj)

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
    """Create VarTypeInfo with proper handling of Annotated types"""
    basetype = tgttype
    extras = None

    if annotation is not None and is_Annotated(annotation):
        args = get_args(annotation)
        if args:
            basetype, *extras_ = args
            extras = tuple(extras_) if extras_ else None

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
) -> tuple[Callable[..., Any], list[Any], dict[str, Any]]:
    """Recursively unwrap partial functions"""
    partial_kwargs = {}
    partial_args = []

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


# map_class_fields function removed - users should choose specific mapping strategy


def map_init_field(
    cls: type,
    bt_default_fallback: bool = True,
    localns: Optional[dict[str, Any]] = None,
) -> list[VarTypeInfo]:
    """Map fields from __init__ method"""
    init_method = getattr(cls, "__init__")

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
    localns: Optional[dict[str, Any]] = None,
) -> list[VarTypeInfo]:
    """Map dataclass fields"""
    hints = get_safe_type_hints(cls, localns)
    items = [(field.name, field) for field in fields(cls)]

    return [
        field_factory(obj, hints.get(name), bt_default_fallback) for name, obj in items
    ]


def map_model_fields(
    cls: type,
    bt_default_fallback: bool = True,
    localns: Optional[dict[str, Any]] = None,
) -> list[VarTypeInfo]:
    """Map model fields from type hints and class attributes"""
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


def map_return_type(
    func: Callable[..., Any], localns: Optional[dict[str, Any]] = None
) -> VarTypeInfo:
    """Map function return type"""
    sig = inspect.signature(func)
    hints = get_safe_type_hints(func, localns)
    raw_return_type = hints.get("return", sig.return_annotation)

    if raw_return_type is inspect.Signature.empty:
        raw_return_type = None

    return make_funcarg(
        name=func.__name__,
        tgttype=raw_return_type,
        annotation=raw_return_type,
    )


def get_return_type(func: Callable[..., Any]) -> Optional[Type[Any]]:
    """Get function return type"""
    returntype = map_return_type(func)
    return returntype.basetype


def map_func_args(
    func: Callable[..., Any],
    localns: Optional[dict[str, Any]] = None,
    bt_default_fallback: bool = True,
) -> Tuple[Sequence[VarTypeInfo], VarTypeInfo]:
    """Map function arguments and return type"""
    funcargs = get_func_args(func, localns, bt_default_fallback)
    return_type = map_return_type(func, localns)
    return funcargs, return_type


def get_func_args(
    func: Callable[..., Any],
    localns: Optional[dict[str, Any]] = None,
    bt_default_fallback: bool = True,
) -> Sequence[VarTypeInfo]:
    """Get function arguments as VarTypeInfo list"""
    # Handle partial functions
    original_func, partial_args, partial_kwargs = unwrap_partial(func)

    sig = inspect.signature(original_func)
    hints = get_safe_type_hints(original_func, localns)

    funcargs: list[VarTypeInfo] = []
    param_names = list(sig.parameters.keys())

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


def get_field_type_(
    tgt: Type[Any],
    fieldname: str,
    localns: Optional[dict[str, Any]] = None,
) -> Optional[Type[Any]]:
    """Get field type from various sources"""
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
    localns: Optional[dict[str, Any]] = None,
) -> Optional[Type[Any]]:
    """Get field type, unwrapping Annotated if present"""
    btype = get_field_type_(tgt, fieldname, localns)
    if btype is not None and is_Annotated(btype):
        args = get_args(btype)
        if args:
            btype = args[0]
    return btype
