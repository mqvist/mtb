from __future__ import annotations

from abc import ABC, abstractmethod
from collections import namedtuple
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import NamedTuple, cast


import hypothesis.strategies as st
from hypothesis import assume
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    initialize,
    precondition,
    rule,
)
from mtb.proxy import make_proxy, Call


class ActionNotEnabled(Exception):
    def __init__(self, action, state_name):
        msg = f"Action {action} is not enabled in state {state_name}"
        super().__init__(msg)


def action(func):
    func._action = True
    return func


class Card(NamedTuple):
    name: str
    pin: str


MenuItem = Enum("MenuItem", "withdraw balance quit")
StateIdle = namedtuple("StateIdle", "")
StateMenu = namedtuple("StateMenu", "")
StateReturnCard = namedtuple("ReturnCard", "")
StateWithdraw = namedtuple("Withdraw", "")
StateBalance = namedtuple("Balance", "")


class StateEnterPin(NamedTuple):
    card: Card
    pin_tries: int = 0


class AtmIf(ABC):
    @abstractmethod
    def init(self):
        pass

    @abstractmethod
    def teardown(self):
        pass

    @abstractmethod
    def insert_card(self, card: Card) -> int:
        pass

    @abstractmethod
    def enter_pin(self, pin: str):
        pass

    @abstractmethod
    def cancel(self):
        pass

    @abstractmethod
    def return_card(self):
        pass

    @abstractmethod
    def choose_menu_item(self, item: MenuItem):
        pass


@dataclass
class AtmOracle(AtmIf):
    state: NamedTuple

    def init(self):
        pass

    def teardown(self):
        pass

    @action
    def insert_card(self, card: Card):
        self.state = StateEnterPin(card)

    @action
    def enter_pin(self, pin: str):
        card, pin_tries = cast(StateEnterPin, self.state)
        assert pin_tries < 3
        if pin == card.pin:
            self.state = StateMenu()
        elif pin_tries >= 2:
            self.state = StateReturnCard()
        else:
            self.state = StateEnterPin(card, pin_tries + 1)

    @action
    def cancel(self):
        self.state = StateReturnCard()

    @action
    def return_card(self):
        self.state = StateIdle()

    @action
    def choose_menu_item(self, item: MenuItem):
        match item:
            case MenuItem.withdraw:
                self.state = StateWithdraw()
            case MenuItem.balance:
                self.state = StateBalance()
            case MenuItem.quit:
                self.state = StateReturnCard()
            case _:
                assert False, item

    @action
    def choose_withdraw_amount(self, amount: Decimal):
        pass


@dataclass
class RealAtm(AtmIf):
    card: Card | None = None
    pin_tries: int = 0
    pin_ok: bool = False
    canceled: bool = False

    def init(self):
        pass

    def teardown(self):
        pass

    def insert_card(self, card: Card):
        assert not self.card
        assert self.pin_tries == 0
        assert not self.pin_ok
        assert not self.canceled
        self.card = card

    def enter_pin(self, pin: str):
        assert self.card
        assert self.pin_tries < 3
        assert not self.pin_ok
        assert not self.canceled
        if pin == self.card.pin:
            self.pin_ok = True
        elif self.pin_tries >= 1:
            self.canceled = True
        else:
            self.pin_tries += 1

    def cancel(self):
        assert self.card
        self.canceled = True

    def return_card(self):
        assert self.card
        assert self.canceled
        self.card = None
        self.pin_tries = 0
        self.pin_ok = False
        self.canceled = False

    def choose_menu_item(self, item: MenuItem):
        assert self.card
        assert self.pin_ok
        match item:
            case MenuItem.withdraw:
                # self.state = "withdraw"
                pass
            case MenuItem.balance:
                # self.state = "balance"
                pass
            case MenuItem.quit:
                # self.state = "return card"
                self.canceled = True
            case _:
                assert False, item


class AtmMachine(RuleBasedStateMachine):
    cards = Bundle("cards")
    num_tests = 0
    calls: list[Call] = []

    def __init__(self):
        super().__init__()
        self.oracle = AtmOracle(StateIdle())
        self.real = RealAtm()

    @staticmethod
    def oracle_state(state):
        return lambda self: self.oracle.state == state or isinstance(
            self.oracle.state, state
        )

    @initialize()
    def init(self):
        self.proxy = make_proxy(AtmIf, [self.oracle, self.real], AtmMachine.calls)
        self.proxy.init()
        self.inserted_card: Card | None = None

    def teardown(self):
        self.proxy.teardown()
        print()
        print("\n".join(map(repr, AtmMachine.calls)))

    @rule(target=cards, card=st.builds(Card))
    def add_card(self, card: Card):
        return card

    @precondition(oracle_state(StateIdle))
    @rule(card=cards)
    def insert_card(self, card: Card):
        self.inserted_card = card
        self.proxy.insert_card(card)

    @precondition(oracle_state(StateEnterPin))
    @rule(pin=st.text(), correct=st.booleans())
    def enter_pin(self, pin: str, correct: bool):
        assert self.inserted_card
        if correct:
            pin = self.inserted_card.pin
        else:
            assume(pin != self.inserted_card.pin)
        self.proxy.enter_pin(pin)

    @precondition(oracle_state(StateMenu))
    @rule(item=st.sampled_from(MenuItem))
    def choose_menu_item(self, item: MenuItem):
        self.proxy.choose_menu_item(item)

    @precondition(oracle_state(StateReturnCard))
    @rule()
    def return_card(self):
        self.proxy.return_card()


test = AtmMachine.TestCase
try:
    test().runTest()
except Exception as e:
    print("Failed")
    print("\n".join(map(repr, AtmMachine.calls)))
