from __future__ import annotations
from copy import copy

import logging
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Generic,
    Type,
    TypeVar,
)

from mtb.action import *
from mtb.action import _ACTION_INFO

# Type variables
T = TypeVar("T")
C = TypeVar("C", bound="Component")


@dataclass
class DiagramOptions:
    width: int = 200
    x_offset: int = 0
    y_offset: int = 0


@dataclass
class Component:
    def __post_init__(self):
        self._log = logging.getLogger(self.__class__.__name__)
        self._log.info(f"Initializing {self.name}")
        # Find all actions, output ports, and input ports
        self._actions: list[Action] = []
        self._output_ports: list[PortOut] = []
        self._input_ports: list[PortIn] = []
        for attr_name in dir(self):
            value = getattr(self, attr_name)
            if is_action(value):
                bound_func = value.__get__(self)
                self._actions.append(Action(self, bound_func))
            elif is_port_out(value):
                self._output_ports.append(value)
            elif is_port_in(value):
                self._input_ports.append(value)
        # Find all attributes that look like public variables, i.e., do not
        # start with an underscore
        self._variables = [name for name in vars(self) if not name.startswith("_")]
        self._diagram_options = DiagramOptions()
        # Call init method to allow subclasses to perform initialization
        self.init()

    def init(self):
        # Override this method to perform initialization
        pass

    def __set_name__(self, owner, name):
        # Called when this component is assigned to a variable in a class. This
        # allows us to set the name of the component to the name of the
        # variable.
        self._instance_name = name

    @property
    def name(self):
        name = self.__class__.__name__
        return snake_to_space(name)

    def _get_index(self, item: PortIn | OutPort) -> int:
        i = 1 if self._input_ports else 0
        for dr in self._input_ports:
            if dr is item:
                return i
            i += 1
        if self._output_ports:
            i += 1
        for dp in self._output_ports:
            if dp is item:
                return i
            i += 1
        raise ValueError("{item} not found")


def snake_to_space(name):
    parts = [name[0]]
    for c in name[1:]:
        if c.isupper() and not parts[-1][-1].isupper():
            parts.append(c)
        else:
            parts[-1] += c
    return " ".join(parts)
    # return self.__class__.__name__


def camel_to_space(name):
    return name.replace("_", " ")


class _PortDescriptor(Generic[T]):
    def __init__(self, type: Type[T]):
        self.type = type
        self.owner: type | None = None
        self.name: str = ""

    def __str__(self):
        assert self.owner and self.name
        return f"{self.__class__.__name__} {self.owner.__name__}.{self.name}"

    def __set_name__(self, owner: type, name: str):
        self.owner = owner
        self.name = camel_to_space(name)


class PortIn(Generic[T]):
    def __init__(self, descriptor: _PortInDescriptor[T], owner: Component):
        self.descriptor = descriptor
        self.owner = owner

    def connect(self, port_out: PortOut[T]):
        receiver = self._safe_get_receiver()
        action_info = getattr(receiver, _ACTION_INFO)
        action_info.connected = True
        port_out._connect(self)

    def _safe_get_receiver(self) -> Callable[[Component, T], None]:
        if not self.descriptor.receiver:
            raise ModelingError(
                f"{self.descriptor} has no receiver. Did you forget to decorate it?"
            )
        return self.descriptor.receiver

    def _receive(self, value: T):
        receiver = self._safe_get_receiver()
        receiver(self.owner, value)


def is_port_in(v: Any) -> bool:
    """Returns True if v is a PortIn instance."""
    return isinstance(v, PortIn)


class _PortInDescriptor(_PortDescriptor[T], Generic[T]):
    """Descriptor for PortIn instances."""

    def __init__(self, type: Type[T]):
        super().__init__(type)
        self.receiver: Callable[[Any, T], None] | None = None

    def __get__(self, component: Component, objtype=None) -> PortIn[T]:
        attr_name = f"__{self.name}_port_"
        try:
            return getattr(component, attr_name)
        except AttributeError:
            r = PortIn(self, component)
            setattr(component, attr_name, r)
            return r

    def __set__(self, component: Component, value: T):
        raise ModelingError("PortIn cannot be assigned to")

    def _set_receiver(self, f: Callable[[C, T], None]):
        if self.receiver:
            raise ModelingError("Multiple definitions of PortIn receiver not allowed")
        self.receiver = f


def port_in(type: Type[T]) -> _PortInDescriptor[T]:
    return _PortInDescriptor(type)


class PortOut(Generic[T]):
    def __init__(self, desriptor: _PortOutDescriptor[T], owner: Component):
        self.descriptor = desriptor
        self.owner = owner
        self.receivers: list[PortIn[T]] = []
        self.latest_value: T | None = None

    def __repr__(self) -> str:
        return f"PortOut(owner={self.owner._instance_name}, descriptor={self.descriptor.name})"

    def _connect(self, receiver: PortIn[T]):
        self.receivers.append(receiver)
        # Cached ports send their latest value on connect
        if self.descriptor.cached and self.latest_value is not None:
            receiver._receive(self.latest_value)

    def send(self, value: T):
        self.latest_value = copy(value)
        for receiver in self.receivers:
            receiver._receive(self.latest_value)


def is_port_out(v: Any) -> bool:
    return isinstance(v, PortOut)


class _PortOutDescriptor(_PortDescriptor[T], Generic[T]):
    def __init__(self, type: Type[T], cached: bool):
        super().__init__(type)
        self.cached = cached

    def __get__(self, component: Component, objtype=None) -> PortOut[T]:
        assert self.name
        attr_name = f"__{self.name}_connections__"
        try:
            return getattr(component, attr_name)
        except AttributeError:
            c = PortOut(self, component)
            setattr(component, attr_name, c)
            return c

    def __set__(self, *_):
        raise ModelingError("PortOut cannot be assigned to")


def port_out(type: Type[T], cached: bool = True) -> _PortOutDescriptor[T]:
    return _PortOutDescriptor(type, cached)


@dataclass
class System:
    name: str = field(init=False)

    def __post_init__(self):
        self.name = self.__class__.__name__

    @property
    def components(self) -> list[Component]:
        components = []
        for key, value in vars(self.__class__).items():
            if isinstance(value, Component):
                components.append(value)
        return components
