from dataclasses import fields, is_dataclass
from enum import Enum
from inspect import isclass
from typing import Any


def build_tree_node(name: str, var: Any) -> dict:
    if is_dataclass(var):
        children = [
            build_tree_node(
                field.name,
                getattr(var, field.name),
            )
            for field in fields(var)
        ]
        return {
            "id": name,
            "children": children,
        }
    elif var is None:
        return {"id": f"{name}: <undefined>"}
    elif isinstance(var, list):
        children = [build_tree_node(f"[{i}]", item) for i, item in enumerate(var)]

        return {
            "id": f"{name} ({'list' if var else 'empty list'})",
            "children": children,
        }
    elif isinstance(var, dict):
        children = [
            build_tree_node(f"[{format_var(key)}]", value) for key, value in var.items()
        ]

        return {
            "id": f"{name} ({'dict' if var else 'empty dict'})",
            "children": children,
        }
    else:
        return {
            "id": f"{name}: {format_var(var)}",
        }


def mark_node_changes(old_node: dict | None, new_node: dict):
    assert "id" in new_node
    if old_node is None or old_node["id"] != new_node["id"]:
        # Node is new or has been changed
        new_node["changed"] = True
    else:
        # Compare children recursively, independent of order
        old_children = {child["id"]: child for child in old_node.get("children", [])}
        new_children = {child["id"]: child for child in new_node.get("children", [])}

        for child_id, child in new_children.items():
            mark_node_changes(old_children.get(child_id), child)

        if any(child.get("changed") for child in new_children.values()):
            new_node["changed"] = True


def format_name(name: str) -> str:
    return name.replace("_", " ").capitalize()


def format_var(var) -> str:
    var_type = type(var)
    if isclass(var_type) and issubclass(var_type, Enum):
        return var.name
    else:
        return truncate(var)


def truncate(value: Any, length: int = 10) -> str:
    s = str(value)
    if length > 0 and len(s) > length:
        return f"{s[:length]}..."
    return s
