import copy
from enum import Enum
import logging
from argparse import ArgumentParser
from dataclasses import fields, is_dataclass
from inspect import isclass
import traceback
from typing import Any

from nicegui import ui
from mtb import guiutil

from mtb.diagram import render_system
from mtb.model import load_model_from_py_file
from mtb.system import Action, ActionParam, Component, System


model = None
system_name = None


def parse_args():
    global model, system_name
    parser = ArgumentParser()
    parser.add_argument("model")
    parser.add_argument("system", default=None, nargs="?")
    args = parser.parse_args()
    model = load_model_from_py_file(args.model)
    system_name = args.system


class Gui:
    def __init__(self, system: System):
        # Dict for holding references to elements that need to be updated
        self.variable_trees: dict[str, ui.element] = {}
        self.system = system
        self.action_count = 0

        self.render_left_drawer()
        ui.html(render_system(self.system)).classes("w-full h-screen")
        self.render_footer()

    def render_footer(self):
        self.log_height = 96

        async def inc_height():
            if self.log_height >= 256:
                return
            self.log_height += 32
            self.log.style(replace=f"height:{self.log_height}px")

        async def dec_height():
            if self.log_height <= 64:
                return
            self.log_height -= 32
            self.log.style(replace=f"height:{self.log_height}px")

        with ui.footer(elevated=True).classes("p-0 bg-blue-100 gap-0"):
            ui.label("Action log").classes("w-full text-black text-center")
            with ui.row().classes("w-full gap-1 m-1"):
                self.log = (
                    ui.log()
                    .classes("grow text-xs text-black bg-white resize-none")
                    .style(f"height:{self.log_height}px")
                )
                with ui.column().classes("absolute right-1 gap-1 mb-1 self-end group"):
                    ui.button("+", on_click=inc_height).props("dense").classes(
                        "text-xs w-4 collapse group-hover:visible"
                    )
                    ui.button("-", on_click=dec_height).props("dense").classes(
                        "text-xs w-4 collapse group-hover:visible"
                    )

    def render_left_drawer(self):
        with ui.left_drawer(top_corner=True, bottom_corner=True).classes(
            "bg-blue-100"
        ).props("width=350 breakpoint=500"):
            ui.label(f"Components").classes("text-lg text-center")
            for component in self.system.components:
                self.render_component_info(component)

    def update_left_drawer(self):
        for component in self.system.components:
            self.update_component_info(component)

    def render_component_info(self, component: Component):
        with ui.expansion(component.name, icon="", value=True).props(
            'dense expand-separator header-class="text-bold"'
        ):
            with ui.card().classes("p-1 gap-0"):
                self.render_variable_info(component)
                if any(not action.connected for action in component._actions):
                    ui.separator()
                    self.render_action_info(component)

    def update_component_info(self, component):
        self.update_variable_info(component)

    def render_variable_info(self, component: Component):
        with ui.tree(
            [
                guiutil.build_tree_node(name, getattr(component, name))
                for name in component._variables
            ],
            label_key="id",
        ).props("dense no-transition").classes("w-full") as tree:
            # Disable node selection so that clicking a node expands it
            tree.props(remove="v-model:selected")
            self.variable_trees[component.name] = tree
        # Add custom header which highlights changed variables in green
        tree.add_slot(
            "default-header",
            r"""
        <div class="row items-center">
            <div :class="props.node.changed ? 'text-green-500 font-medium' : ''">{{ props.node.id }}</div>
        </div>
    """,
        )

    def update_variable_info(self, component: Component):
        # Update tree nodes with new values and mark changed nodes
        tree = self.variable_trees[component.name]
        old_nodes = tree._props["nodes"]
        new_nodes = [
            guiutil.build_tree_node(name, getattr(component, name))
            for name in component._variables
        ]
        for old_node, new_node in zip(old_nodes, new_nodes):
            guiutil.mark_node_changes(old_node, new_node)
        tree._props["nodes"] = new_nodes
        tree.update()

    def render_action_info(self, component: Component):
        with ui.row().classes("w-full py-2 gap-1 justify-center"):
            if not component._actions:
                ui.label("No actions")
            else:
                for a in component._actions:
                    if a.connected:
                        continue
                    ui.button(
                        guiutil.format_name(a.name),
                        on_click=self.make_action_callback(a),
                    ).props("dense").classes("text-xs")

    def make_action_callback(self, action: Action):
        if action.params:

            async def send_with_args():
                assert len(action.params) == 1
                param = action.params[0]
                default_value = action.get_default_value(param)
                with ui.dialog() as dialog, ui.card():
                    with ui.column().classes("gap-1"):
                        args = {param.name: default_value}
                        ui.label(guiutil.format_name(action.name)).classes("text-base")
                        try:
                            self.make_param_ui_elem(param, args)
                        except Exception as e:
                            ui.notify(
                                traceback.format_exc(),
                                closeBtn=True,
                                position="bottom",
                                icon="error",
                                type="negative",
                                timeout=0,
                                multiline=True,
                                classes="font-mono whitespace-pre-wrap text-xs",
                            )
                            raise
                        with ui.row():
                            ui.button("Ok", on_click=lambda: dialog.submit(args))
                            ui.button("Cancel", on_click=lambda: dialog.submit(None))

                args = await dialog
                if args is not None:
                    action(**args)
                    self.action_count += 1
                    self.log.push(
                        f"{self.action_count}: ➤ {action.owner._instance_name}.{action.name}({', '.join(map(str, args.values()))})"
                    )
                    self.update_left_drawer()

            return send_with_args
        else:
            return lambda: action()

    def make_param_ui_elem(
        self,
        param: ActionParam,
        args: dict[str, Any] | object,
        nested: bool = False,
    ):
        def set_param(args: dict[str, Any] | object, name: str, value: Any):
            if isinstance(args, dict):
                args[name] = value
            else:
                setattr(args, name, value)

        def get_param(args: dict[str, Any] | object, name: str = param.name) -> Any:
            if isinstance(args, dict):
                return args.get(name)
            else:
                return getattr(args, name)

        if isclass(param.type) and issubclass(param.type, Enum):
            values = [value.name for value in param.type]
            ui.label(guiutil.format_name(param.name))
            ui.radio(
                options=values,
                value=get_param(args, param.name).name,
                on_change=lambda e: set_param(args, param.name, param.type[e.value]),  # type: ignore
            ).props("dense")

        elif is_dataclass(param.type):
            if nested:
                ui.label(guiutil.format_name(param.name))
            for field in fields(param.type):
                self.make_param_ui_elem(
                    ActionParam(field.name, field.type),
                    get_param(args, param.name),
                    nested=True,
                )

        elif param.type is str:
            ui.input(
                guiutil.format_name(param.name),
                value=get_param(args, param.name),
                validation={"Please give value": lambda value: len(value) > 0},
                on_change=lambda e: set_param(args, param.name, e.value),
            )

        elif param.type is bool:
            with ui.row().classes("gap-1 items-center"):
                ui.checkbox(
                    value=get_param(args, param.name),
                    on_change=lambda e: set_param(args, param.name, e.value),
                ).props("dense")
                ui.label(f"Enable {guiutil.format_name(param.name)}").classes("p-0")

        elif param.type is int:
            ui.number(
                guiutil.format_name(param.name),
                value=get_param(args, param.name),
                format="%d",
                on_change=lambda e: set_param(args, param.name, int(e.value)),
            )

        elif param.type is str:
            ui.input(
                guiutil.format_name(param.name),
                on_change=lambda e: set_param(args, param.name, int(e.value)),
            )
        else:
            raise NotImplementedError(f"Type {param.type} not supported.")


@ui.page("/", title="MTB")
def index():
    assert model
    assert system_name

    system = model.get_system(system_name)
    assert system
    gui = Gui(system)


if __name__ in {"__main__", "__mp_main__"}:
    logging.basicConfig(level=logging.INFO)
    parse_args()
    ui.run()
