import signal
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from NodeGraphQt import NodeGraph

# import example nodes from the "nodes" sub-package
from examples.nodes import basic_nodes, custom_ports_node, widget_nodes

BASE_PATH = Path(__file__).parent.resolve()


def main():
    # handle SIGINT to make the app terminate on CTRL+C
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QtWidgets.QApplication([])

    # create graph controller.
    graph = NodeGraph()

    # set up context menu for the node graph.
    hotkey_path = Path(BASE_PATH, "hotkeys", "hotkeys.json")
    graph.set_context_menu_from_file(hotkey_path, "graph")

    # registered example nodes.
    graph.register_nodes(
        [
            basic_nodes.BasicNodeA,
            basic_nodes.BasicNodeB,
            custom_ports_node.CustomPortsNode,
            widget_nodes.DropdownMenuNode,
            widget_nodes.TextInputNode,
            widget_nodes.CheckboxNode,
        ]
    )

    # show the node graph widget.
    graph_widget = graph.widget
    graph_widget.resize(1100, 800)
    graph_widget.show()

    # create node with custom text color and disable it.
    n_basic_a = graph.create_node("nodes.basic.BasicNodeA", text_color="#feab20")
    n_basic_a.set_disabled(True)

    # create node and set a custom icon.
    n_basic_b = graph.create_node("nodes.basic.BasicNodeB", name="custom icon")
    n_basic_b.set_icon(Path(BASE_PATH, "star.png"))

    # create node with the custom port shapes.
    n_custom_ports = graph.create_node(
        "nodes.custom.ports.CustomPortsNode", name="custom ports"
    )

    # create node with the embedded QLineEdit widget.
    n_text_input = graph.create_node(
        "nodes.widget.TextInputNode", name="text node", color="#0a1e20"
    )

    # create node with the embedded QCheckBox widgets.
    n_checkbox = graph.create_node("nodes.widget.CheckboxNode", name="checkbox node")

    # create node with the QComboBox widget.
    n_combo_menu = graph.create_node(
        "nodes.widget.DropdownMenuNode", name="combobox node"
    )

    # make node connections.

    # (connect nodes using the .set_output method)
    n_text_input.set_output(0, n_custom_ports.input(0))
    n_text_input.set_output(0, n_checkbox.input(0))
    n_text_input.set_output(0, n_combo_menu.input(0))
    # (connect nodes using the .set_input method)
    n_basic_b.set_input(2, n_checkbox.output(0))
    n_basic_b.set_input(2, n_combo_menu.output(1))
    # (connect nodes using the .connect_to method from the port object)
    port = n_basic_a.input(0)
    port.connect_to(n_basic_b.output(0))

    # auto layout nodes.
    graph.auto_layout_nodes()

    # crate a backdrop node and wrap it around
    # "custom port node" and "group node".
    n_backdrop = graph.create_node("Backdrop")
    n_backdrop.wrap_nodes([n_custom_ports, n_combo_menu])

    # fit nodes to the viewer.
    graph.clear_selection()
    graph.fit_to_selection()

    app.exec()


if __name__ == "__main__":
    main()
