from dataclasses import dataclass
from mtb.guiutil import *


def test_build_tree_simple_values():
    assert build_tree_node("name", 1) == {"id": "name: 1"}
    assert build_tree_node("name", 1.0) == {"id": "name: 1.0"}
    assert build_tree_node("name", "value") == {"id": "name: value"}
    assert build_tree_node("name", None) == {"id": "name: <undefined>"}
    assert build_tree_node("name", True) == {"id": "name: True"}


def test_build_tree_lists():
    assert build_tree_node("name", []) == {"id": "name (empty list)", "children": []}
    assert build_tree_node("name", [1, 2]) == {
        "id": "name (list)",
        "children": [
            {
                "id": "[0]: 1",
            },
            {
                "id": "[1]: 2",
            },
        ],
    }


def test_build_tree_dicts():
    assert build_tree_node("name", {}) == {"id": "name (empty dict)", "children": []}
    assert build_tree_node("name", {"a": 1, "b": 2}) == {
        "id": "name (dict)",
        "children": [
            {
                "id": "[a]: 1",
            },
            {
                "id": "[b]: 2",
            },
        ],
    }


def test_build_tree_dataclasses():
    @dataclass
    class A:
        b: int = 0
        c: str = "c"

    assert build_tree_node("name", A()) == {
        "id": "name",
        "children": [
            {
                "id": "b: 0",
            },
            {
                "id": "c: c",
            },
        ],
    }


def test_mark_new_tree_elements_simple():
    old_tree = {
        "id": "a",
    }
    new_tree = {
        "id": "b",
    }
    mark_node_changes(old_tree, new_tree)
    assert new_tree == {
        "id": "b",
        "changed": True,
    }


def test_mark_new_tree_elements():
    old_tree = {
        "id": "name",
        "children": [
            {
                "id": "a: 0",
            },
            {
                "id": "b: 0",
            },
            {
                "id": "c: c",
                "children": [
                    {
                        "id": "d: d",
                    },
                ],
            },
        ],
    }
    new_tree = {
        "id": "name",
        "children": [
            {
                "id": "a: 0",
            },
            {
                "id": "b: 1",
            },
            {
                "id": "c: c",
                "children": [
                    {
                        "id": "d: e",
                    },
                ],
            },
            {
                "id": "f: f",
            },
        ],
    }
    mark_node_changes(old_tree, new_tree)
    assert new_tree == {
        "id": "name",
        "children": [
            {
                "id": "a: 0",
            },
            {
                "id": "b: 1",
                "changed": True,
            },
            {
                "id": "c: c",
                "children": [
                    {
                        "id": "d: e",
                        "changed": True,
                    },
                ],
                "changed": True,
            },
            {
                "id": "f: f",
                "changed": True,
            },
        ],
        "changed": True,
    }
