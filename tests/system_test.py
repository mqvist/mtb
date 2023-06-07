import pytest
from mtb.system import *


def test_action_with_no_args():
    class C(Component):
        var: int = 0

        @action
        def a(self):
            self.var = 1

    c = C()
    a = c._actions[0]
    assert len(a.params) == 0
    a()
    assert c.var == 1


def test_action_with_args():
    class C(Component):
        var: int = 0

        @action
        def a(self, inc: int):
            self.var += inc

    c = C()
    a = c._actions[0]
    assert len(a.params) == 1
    assert a.params[0].name == "inc"
    assert a.params[0].type == int
    a(2)
    assert c.var == 2


def test_action_with_missing_param_type_annotation():
    class C(Component):
        var: int = 0

        @action
        def a(self, inc):
            self.var += inc

    with pytest.raises(ModelingError):
        c = C()


def test_latest_value_is_received_on_connect():
    class C1(Component):
        d_in = port_in(int)
        d_out = port_out(int)

        d: int = 0

        @receiver(d_in)
        def receive_d1(self, d: int):
            self.d = d

    c = C1()
    c.d_out.send(1)
    c.d_in.connect(c.d_out)
    assert c.d == 1


def test_latest_value_is_not_received_on_connect_when_output_port_is_not_cached():
    class C1(Component):
        d_in = port_in(int)
        d_out = port_out(int, cached=False)

        d: int = 0

        @receiver(d_in)
        def receive_d1(self, d: int):
            self.d = d

    c = C1()
    c.d_out.send(1)
    c.d_in.connect(c.d_out)
    assert c.d == 0


def test_connected_receiver():
    class C1(Component):
        d_in = port_in(int)
        d_out = port_out(int)

        d: int = 0

        @receiver(d_in)
        def receive_d1(self, d: int):
            self.d = d

    c = C1()
    a = c._actions[0]
    assert not a.connected
    c.d_in.connect(c.d_out)
    assert a.connected


def test_action_with_default_value():
    class C(Component):
        d: int = 0

        @action(d=lambda self: self.d)
        def set_d(self, d: int):
            self.d = d

    c = C()
    a = c._actions[0]
    assert a.get_default_value(a.params[0]) == 0
    a(1)
    assert a.get_default_value(a.params[0]) == 1
