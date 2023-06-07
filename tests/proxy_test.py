from unittest.mock import Mock
from mtb.proxy import *
from examples.demo import action


class Class:
    @action
    def call(self, n: int, t: str):
        pass


def test_foo():
    o1 = Mock()
    o2 = Mock()
    calls = []
    p = make_proxy(Class, [o1, o2], calls)
    p.call(1, "test")

    assert calls == [Call(name="call", args=(1, "test"), kwds={})]
    o1.call.assert_called_once_with(1, "test")
    o2.call.assert_called_once_with(1, "test")
