from typing import Iterator
import svg

from mtb.system import Component, System


VIEW_BOX_SIZE = 1000
COMPONENT_CORNER_RADIUS = 10
COMPONENT_STROKE_WIDTH = 2
ARROW_STROKE_WIDTH = 1.5
FONT_SIZE = 12


def component_height(component: Component) -> float:
    io_item_count = len(component._output_ports) + len(component._input_ports)
    if component._output_ports:
        io_item_count += 1
    if component._input_ports:
        io_item_count += 1
    return (io_item_count + 2) * FONT_SIZE + 5


def component_width(component: Component) -> float:
    return component._diagram_options.width


def io_elem_y_offset(component: Component, i: int):
    return -component_height(component) / 2 + (i + 2) * FONT_SIZE + 5


def render_system(system: System) -> str:
    components = list(system.components)
    elements = [render_component(component) for component in components]
    elements += render_io_arrows(components)
    canvas = svg.SVG(
        width=svg.Length(100, "%"),
        height=svg.Length(100, "%"),
        viewBox=svg.ViewBoxSpec(
            min_x=-VIEW_BOX_SIZE / 2,
            min_y=-VIEW_BOX_SIZE / 2,
            width=VIEW_BOX_SIZE,
            height=VIEW_BOX_SIZE,
        ),
        preserveAspectRatio=svg.PreserveAspectRatio("xMidYMid", "slice"),
        elements=elements,
    )

    return str(canvas)


def render_component(component: Component) -> svg.Element:
    return svg.G(
        transform_origin="center",
        transform=[
            svg.Translate(
                x=component._diagram_options.x_offset,
                y=component._diagram_options.y_offset,
            )
        ],
        elements=[
            svg.Rect(
                x=-component_width(component) / 2,
                y=-component_height(component) / 2,
                rx=COMPONENT_CORNER_RADIUS,
                ry=COMPONENT_CORNER_RADIUS,
                width=component_width(component) - COMPONENT_STROKE_WIDTH,
                height=component_height(component) - COMPONENT_STROKE_WIDTH,
                fill="#88bbff",
                stroke="black",
                stroke_width=COMPONENT_STROKE_WIDTH,
                class_=["cursor-move"],
                onload="makeDraggable(evt)",
            ),
            svg.Text(
                text=component.name,
                x=0,
                y=-component_height(component) / 2 + FONT_SIZE,
                font_size=FONT_SIZE,
                font_weight="bold",
                fill="black",
                dominant_baseline="middle",
                text_anchor="middle",
                # text_decoration="underline",
                # textLength=component_width(component) - 20,
            ),
            *render_io_elements(component),
        ],
    )


def render_io_elements(component: Component) -> Iterator[svg.Element]:
    i = 0
    x = -component_width(component) / 2 + 20
    if component._input_ports:
        yield render_section_label(
            x - 10, io_elem_y_offset(component, 0), "input ports"
        )
        i += 1
    for dr in component._input_ports:
        y = io_elem_y_offset(component, i)
        text = dr.descriptor.name
        yield svg.Text(text=text, font_size=FONT_SIZE, x=x, y=y, text_anchor="start")
        i += 1
    if component._output_ports:
        yield render_section_label(
            x - 10, io_elem_y_offset(component, i), "output ports"
        )
        i += 1
    for dp in component._output_ports:
        y = io_elem_y_offset(component, i)
        text = dp.descriptor.name
        yield svg.Text(text=text, font_size=FONT_SIZE, x=x, y=y, text_anchor="start")
        i += 1


def render_section_label(x, y, label):
    return svg.Text(
        text=label,
        font_size=FONT_SIZE - 3,
        font_style="italic",
        font_weight="bold",
        # text_decoration="underline",
        x=x,
        y=y - 1,
        text_anchor="start",
    )


def render_io_arrows(components: list[Component]) -> list[svg.Element]:
    arrows = []
    for c in components:
        for output in c._output_ports:
            for input in output.receivers:
                start_x = output.owner._diagram_options.x_offset
                end_x = input.owner._diagram_options.x_offset

                start_offset = component_width(output.owner) / 2 - 10
                end_offset = component_width(input.owner) / 2 - 10
                # Check which way the arrow should point
                if start_x < end_x:
                    # Left to right
                    x1 = start_x + start_offset
                    x2 = end_x - end_offset
                else:
                    # Right to left
                    x1 = start_x - start_offset
                    x2 = end_x + end_offset

                i = output.owner._get_index(output)
                y1 = (
                    output.owner._diagram_options.y_offset
                    + io_elem_y_offset(output.owner, i)
                    - FONT_SIZE / 3
                )
                i = input.owner._get_index(input)
                y2 = (
                    input.owner._diagram_options.y_offset
                    + io_elem_y_offset(input.owner, i)
                    - FONT_SIZE / 3
                )
                arrows.append(render_arrow(x1, y1, x2, y2))

    return arrows


def render_arrow(x1: float, y1: float, x2: float, y2: float) -> svg.Element:
    cd = (x2 - x1) * 0.7
    return svg.G(
        elements=[
            svg.Defs(
                elements=[
                    svg.Marker(
                        id="arrowhead",
                        viewBox=svg.ViewBoxSpec(0, 0, 10, 10),
                        refX=4,
                        refY=5,
                        markerWidth=6,
                        markerHeight=6,
                        orient="auto",
                        elements=[
                            svg.Path(
                                d=[svg.M(1, 2), svg.L(8, 5), svg.L(1, 8), svg.Z()],
                                fill="lightgreen",
                                stroke="black",
                                stroke_width=1.2,
                            )
                        ],
                    ),
                    svg.Marker(
                        id="dot",
                        viewBox=svg.ViewBoxSpec(0, 0, 10, 10),
                        refX=5,
                        refY=5,
                        markerWidth=6,
                        markerHeight=6,
                        orient="auto",
                        elements=[
                            svg.Circle(
                                cx=5,
                                cy=5,
                                r=3,
                                fill="orange",
                                stroke="black",
                                stroke_width=1.2,
                            )
                        ],
                    ),
                ]
            ),
            svg.G(
                elements=[
                    svg.Path(
                        id="arrowLeft",
                        d=[
                            svg.M(x1, y1),
                            svg.C(x1 + cd, y1, x2 - cd, y2, x2, y2),
                        ],
                        fill="none",
                        stroke="black",
                        stroke_width=ARROW_STROKE_WIDTH,
                        # stroke_dasharray=[5, 1],
                        marker_start="url(#dot)",
                        marker_end="url(#arrowhead)",
                        class_=["hover:stroke-[2.5px]"],
                    ),
                ],
            ),
        ],
    )
