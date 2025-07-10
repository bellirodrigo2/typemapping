import inspect
import sys
from dataclasses import MISSING, Field, dataclass, fields, is_dataclass
from functools import partial
from inspect import Parameter, signature

from typing_extensions import Annotated as typing_extensions_Annotated
from typing_extensions import (
    Any,
    Callable,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

try:
    from typing import Annotated as typing_Annotated
except ImportError:
    typing_Annotated = None

T = TypeVar("T")


def is_Annotated(bt: Optional[Type[Any]]) -> bool:
    origin = get_origin(bt)
    return origin in (typing_extensions_Annotated, typing_Annotated)


def is_equal_type(t1: Type[Any], t2: Type[Any]) -> bool:
    return get_origin(t1) == get_origin(t2) and get_args(t1) == get_args(t2)


@dataclass
class VarTypeInfo:
    name: str
    argtype: Optional[Type[Any]]
    basetype: Optional[Type[Any]]
    default: Optional[Any]
    has_default: bool = False
    extras: Optional[tuple[Any]] = None

    @property
    def origin(self) -> Optional[Type[Any]]:
        return get_origin(self.basetype)

    @property
    def args(self) -> tuple[Any, ...]:
        return get_args(self.basetype)

    def isequal(self, arg: Any) -> bool:
        if is_Annotated(arg):
            return self.isequal(get_args(arg)[0])
        if get_origin(arg) is None:
            return self.basetype == arg
        return self.origin == get_origin(arg) and self.args == get_args(arg)

    def istype(self, tgttype: type) -> bool:
        if is_Annotated(tgttype):
            return self.isequal(get_args(tgttype)[0])
        try:
            return self.isequal(tgttype) or (issubclass(self.basetype, tgttype))  # type: ignore
        except TypeError:
            return False

    def getinstance(self, tgttype: Type[T], default: bool = True) -> Optional[T]:
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
        return self.getinstance(tgttype, default) is not None


class _NoDefault:
    def __repr__(self) -> str:
        return "NO_DEFAULT"

    def __str__(self) -> str:
        return "NO_DEFAULT"


NO_DEFAULT = _NoDefault()


def get_safe_type_hints(
    obj: Any, localns: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """
    Get type hints, including ForwardRef for Self
    """
    if inspect.isclass(obj):
        cls = obj
    elif inspect.isfunction(obj) or inspect.ismethod(obj):
        cls = obj.__qualname__.split(".")[0]
        cls = getattr(sys.modules[obj.__module__], cls, None)
    else:
        cls = None

    globalns = vars(sys.modules[obj.__module__]).copy()

    if cls and inspect.isclass(cls):
        globalns[cls.__name__] = cls
    return get_type_hints(obj, globalns=globalns, localns=localns, include_extras=True)


def resolve_class_default(param: Parameter) -> tuple[bool, Any]:
    if param.default is not Parameter.empty:
        return True, param.default
    return False, NO_DEFAULT


def resolve_dataclass_default(field: Field[Any]) -> tuple[bool, Any]:
    if field.default is not MISSING:
        return True, field.default
    elif field.default_factory is not MISSING:
        return True, field.default_factory
    return False, NO_DEFAULT


def field_factory(
    obj: Union[Field[Any], Parameter],
    hint: Any,
    bt_default_fallback: bool = True,
) -> VarTypeInfo:
    resolve_default = (
        resolve_class_default
        if isinstance(obj, Parameter)
        else resolve_dataclass_default
    )

    has_default, default = resolve_default(obj)
    if hint is not inspect._empty:
        argtype = hint
    elif bt_default_fallback:
        argtype = type(default) if default not in (NO_DEFAULT, None) else None
    else:
        argtype = None

    funcarg = make_funcarg(
        name=obj.name,
        tgttype=argtype,
        annotation=hint,
        default=default,
        has_default=has_default,
    )
    return funcarg


def make_funcarg(
    name: str,
    tgttype: Type[Any],
    annotation: Optional[Type[Any]] = None,
    default: Any = None,
    has_default: bool = False,
) -> VarTypeInfo:

    basetype = tgttype
    extras = None

    if annotation is not None and is_Annotated(annotation):
        basetype, *extras_ = get_args(annotation)
        extras = tuple(extras_)
    return VarTypeInfo(
        name=name,
        argtype=tgttype,
        basetype=basetype,
        default=default,
        extras=extras,
        has_default=has_default,
    )


def map_class_fields(cls: type, bt_default_fallback: bool = True) -> list[VarTypeInfo]:
    init_method = getattr(cls, "__init__", None)
    if is_dataclass(cls):
        return map_dataclass_fields(cls, bt_default_fallback)
    elif init_method and not isinstance(init_method, type(object.__init__)):
        return map_init_field(cls, bt_default_fallback)
    else:
        return map_model_fields(cls, bt_default_fallback)


def map_init_field(
    cls: type,
    bt_default_fallback: bool = True,
    localns: Optional[dict[str, Any]] = None,
) -> list[VarTypeInfo]:
    init_method = getattr(cls, "__init__", None)
    if not init_method:
        raise ValueError("No __init__ defined for the class")
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
    hints = get_safe_type_hints(cls, localns)
    items = [
        (
            name,
            Parameter(
                name,
                Parameter.POSITIONAL_OR_KEYWORD,
                default=getattr(cls, name, Parameter.empty),
            ),
        )
        for name in hints
    ]
    return [
        field_factory(obj, hints.get(name), bt_default_fallback) for name, obj in items
    ]


def map_return_type(
    func: Callable[..., Any], localns: Optional[dict[str, Any]] = None
) -> VarTypeInfo:
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
    returntype = map_return_type(func)
    return returntype.basetype


def map_func_args(
    func: Callable[..., Any],
    localns: Optional[dict[str, Any]] = None,
    bt_default_fallback: bool = True,
) -> Tuple[Sequence[VarTypeInfo], VarTypeInfo]:

    funcargs = get_func_args(func, localns, bt_default_fallback)
    return_type = map_return_type(func, localns)

    return funcargs, return_type


def get_func_args(
    func: Callable[..., Any],
    localns: Optional[dict[str, Any]] = None,
    bt_default_fallback: bool = True,
) -> Sequence[VarTypeInfo]:
    partial_args = {}

    if isinstance(func, partial):
        partial_args = func.keywords or {}
        func = func.func

    sig = inspect.signature(func)
    hints = get_safe_type_hints(func, localns)

    funcargs: list[VarTypeInfo] = []

    for name, param in sig.parameters.items():
        if name in partial_args:
            continue
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue

        annotation: type = hints.get(name, param.annotation)
        arg = field_factory(param, annotation, bt_default_fallback)
        funcargs.append(arg)

    return funcargs


def get_field_type_(
    tgt: Type[Any],
    fieldname: str,
    localns: Optional[dict[str, Any]] = None,
) -> Optional[Type[Any]]:
    cls_th = get_safe_type_hints(tgt, localns)
    if fieldname in cls_th:
        return cls_th[fieldname]

    try:
        init_th = get_safe_type_hints(tgt.__init__, localns)
        if fieldname in init_th:
            return init_th[fieldname]
    except AttributeError:
        pass

    attr = getattr(tgt, fieldname, None)
    if attr is None:
        return None
    ret = "return"
    try:
        attr_th = get_type_hints(attr)
        if ret in attr_th:
            return attr_th[ret]
    except TypeError:
        pass
    try:
        prop_th = get_safe_type_hints(attr.fget, localns)
        if ret in prop_th:
            return prop_th[ret]
    except AttributeError:
        pass
    return None


def get_field_type(
    tgt: Type[Any],
    fieldname: str,
    localns: Optional[dict[str, Any]] = None,
) -> Optional[Type[Any]]:
    btype = get_field_type_(tgt, fieldname, localns)
    if btype is not None and is_Annotated(btype):
        btype = get_args(btype)[0]
    return btype
