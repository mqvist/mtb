from abc import ABC
from copy import copy
from dataclasses import dataclass, is_dataclass
import enum
from functools import partial
from inspect import getmembers, isabstract, isclass, isfunction, ismethod
from types import FunctionType, new_class
from typing import Any, Callable, Type, TypeVar


@dataclass(frozen=True)
class Call:
    name: str
    args: tuple[Any, ...]
    kwds: dict[str, Any]

    def __repr__(self) -> str:
        return f"{self.name}({', '.join(map(arg_to_str, self.args))})"


def arg_to_str(arg: Any) -> str:
    match arg:
        case arg if isinstance(arg, enum.Enum):
            return str(arg)
        case _:
            return repr(arg)


T = TypeVar("T")


def make_proxy(cls: Type[T], proxy_for: list[object], calls: list[Call]) -> T:
    if not isclass(cls):
        raise ValueError(f"Argument {cls} is not an class")

    def create_body(ns: dict[str, Any]):
        ns["_calls"] = calls
        ns["_proxy_for"] = proxy_for
        for name, func in getmembers(cls, isfunction):
            if not hasattr(func, "_action"):
                continue
            ns[name] = make_proxy_method(name)

    proxy = new_class(f"{cls.__name__}Proxy", (cls,), None, create_body)
    return proxy()


def make_proxy_method(name: str) -> Callable:
    def proxy_func(self, *args: Any, **kwds: Any):
        self._calls.append(Call(name, args, kwds))
        for obj in self._proxy_for:
            func = getattr(obj, name)
            func(*args, **kwds)

    return proxy_func
