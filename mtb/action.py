from __future__ import annotations
from copy import copy

from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
from inspect import getfullargspec
from typing import (
    Any,
    Callable,
    Generic,
    ParamSpec,
    Type,
    TypeVar,
    TypeVarTuple,
    overload,
)

from mtb.base import *
import mtb.system as system

_ACTION_INFO = "__mtb_action"
P = ParamSpec("P")
T = TypeVar("T")
C = TypeVar("C", bound="system.Component")
Ts = TypeVarTuple("Ts")


@dataclass
class Action(Generic[P]):
    owner: system.Component
    action_func: Callable[P, None]
    params: tuple[ActionParam] = field(init=False)

    def __post_init__(self):
        params = []
        info = getattr(self.action_func, _ACTION_INFO)
        argspec = getfullargspec(self.action_func)
        for arg in argspec.args:
            if arg == "self":
                continue
            elif arg not in argspec.annotations:
                raise ModelingError(
                    f"Missing type annotation for action {self.name!r} param {arg!r}"
                )
            get_default = info.default_getters.get(arg)

            params.append(ActionParam(arg, argspec.annotations[arg], get_default))
        self.params = tuple(params)

    @property
    def name(self) -> str:
        return self.action_func.__name__

    @property
    def connected(self) -> bool:
        info = getattr(self.action_func, _ACTION_INFO)
        return info.connected

    def __call__(self, *args: P.args, **kwargs: P.kwargs):
        self.action_func(*args, **kwargs)

    def get_default_value(self, param: ActionParam) -> Any:
        info = getattr(self.action_func, _ACTION_INFO)
        return param.get_default_value(self.owner)


@dataclass
class ActionParam(Generic[T]):
    name: str
    type: Type[T]
    get_default: None | Callable[[Action], T] = None

    def get_default_value(self, owner) -> T:
        default_value = self.get_default(owner) if self.get_default else None
        if default_value is not None:
            # Make a copy of the default value to avoid modifying the original
            # value when the action is called
            return copy(default_value)
        else:
            return get_type_default(self.type)


def get_type_default(type: Type[T]) -> T:
    """Return a default value for the given type."""
    if issubclass(type, Enum):
        # Use the first enum value as default
        return list(type)[0]
    elif is_dataclass(type):
        # Create an instance of the dataclass with default values for all fields
        args = {field.name: get_type_default(field.type) for field in fields(type)}
        return type(**args)
    else:
        # Use the default constructor for other types
        return type()


@dataclass
class ActionInfo:
    default_getters: dict[str, Callable] = field(default_factory=dict)
    connected: bool = False


@overload
def action(arg: Callable[..., None]) -> Callable[..., None]:
    ...


@overload
def action(
    arg: None = ...,
    **kwargs: Callable,
) -> Callable[[Callable[..., None]], Callable[..., None]]:
    ...


def action(
    arg: None | Callable[..., None] = None,
    **kwargs: Callable,
) -> Callable[..., None] | Callable[[Callable[..., None]], Callable[..., None]]:
    if arg is None:

        def deco(f: Callable[[C, *Ts], None]) -> Callable[[C, *Ts], None]:
            setattr(f, _ACTION_INFO, ActionInfo(default_getters=kwargs))
            return f

        return deco
    else:
        setattr(arg, _ACTION_INFO, ActionInfo())
        return arg


def is_action(f: Callable) -> bool:
    return getattr(f, _ACTION_INFO, False)


def receiver(
    arg: system._PortInDescriptor[T],
) -> Callable[[Callable[[C, T], None]], Callable[[C, T], None]]:
    def deco(f: Callable[[C, T], None]) -> Callable[[C, T], None]:
        arg._set_receiver(f)
        setattr(f, _ACTION_INFO, ActionInfo())
        return f

    return deco
