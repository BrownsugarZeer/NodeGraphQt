from collections import OrderedDict
from typing import List

from NodeGraphQt.base.commands import (
    NodeVisibleCmd,
    NodeWidgetVisibleCmd,
    PropertyChangedCmd,
)
from NodeGraphQt.nodes.base_model import NodeObject
from NodeGraphQt.ports.base_model import Port
from NodeGraphQt.constants import (
    NodePropWidgetEnum,
    PortTypeEnum,
)
from NodeGraphQt.errors import (
    PortError,
    PortRegistrationError,
    NodeWidgetError,
)
from NodeGraphQt.widgets.node_widgets import (
    NodeBaseWidget,
    NodeLineEdit,
)


class BaseNode(NodeObject):
    """
    The ``NodeGraphQt.BaseNode`` class is the base class for nodes that allows
    port connections from one node to another.

    .. inheritance-diagram:: NodeGraphQt.BaseNode

    .. image:: ../_images/node.png
        :width: 250px

    example snippet:

    .. code-block:: python
        :linenos:

        from NodeGraphQt import BaseNode

        class ExampleNode(BaseNode):

            # unique node identifier domain.
            __identifier__ = 'io.jchanvfx.github'

            # initial default node name.
            NODE_NAME = 'My Node'

            def __init__(self):
                super().__init__()

                # create an input port.
                self.add_input('in')

                # create an output port.
                self.add_output('out')
    """

    NODE_NAME = "Node"

    def __init__(self):
        super().__init__()
        self._inputs = []  # NOTE: List[Port]
        self._outputs = []  # NOTE: List[Port]

    def update_model(self):
        """
        Update the node model from view.
        """
        for name, val in self.view.properties.items():
            if name in ["inputs", "outputs"]:
                continue
            self.model.set_property(name, val)

        for name, widget in self.view.widgets.items():
            self.model.set_property(name, widget.get_value())

    def set_property(self, name, value, push_undo=True):
        """
        Set the value on the node custom property.

        Note:
            When setting the node ``"name"`` property a new unique name will be
            used if another node in the graph has the same node name.

        Args:
            name (str): name of the property.
            value (object): property data (python built in types).
            push_undo (bool): register the command to the undo stack. (default: True)
        """
        # prevent signals from causing an infinite loop.
        if self.model.get_property(name) is value:
            return

        if name == "visible":
            if self.graph:
                undo_cmd = NodeVisibleCmd(self, value)
                if push_undo:
                    self.graph.undo_stack().push(undo_cmd)
                else:
                    undo_cmd.redo()
                return
        elif name == "disabled":
            # redraw the connected pipes in the scene.
            ports = self.view.inputs + self.view.outputs
            for port in ports:
                for pipe in port.connected_pipes:
                    pipe.update()

        # super().set_property(name, value, push_undo)
        # prevent nodes from have the same name.
        if self.graph:
            if name == "name":
                value = self.graph.get_unique_name(value)
                self.NODE_NAME = value

            undo_cmd = PropertyChangedCmd(self, name, value)
            if name == "name":
                undo_cmd.setText(f"renamed '{self.view.name}' to '{value}'")
            if push_undo:
                undo_stack = self.graph.undo_stack()
                undo_stack.push(undo_cmd)
            else:
                undo_cmd.redo()

        # redraw the node for custom properties.
        if self.model.is_custom_property(name):
            self.view.draw_node()

    def set_layout_direction(self, value=0):
        """
        Sets the node layout direction to either horizontal or vertical on
        the current node only.

        `Implemented in` ``v0.3.0``

        See Also:
            :meth:`NodeGraph.set_layout_direction`,
            :meth:`NodeObject.layout_direction`


        Warnings:
            This function does not register to the undo stack.

        Args:
            value (int): layout direction mode.
        """
        # base logic to update the model and view attributes only.
        self.view.layout_direction = value
        # redraw the node.
        self._view.draw_node()

    def widgets(self):
        """
        Returns all embedded widgets from this node.

        See Also:
            :meth:`BaseNode.get_widget`

        Returns:
            dict: embedded node widgets. {``property_name``: ``node_widget``}
        """
        return self.view.widgets

    def get_widget(self, name):
        """
        Returns the embedded widget associated with the property name.

        See Also:
            :meth:`BaseNode.add_combo_menu`,
            :meth:`BaseNode.add_text_input`,
            :meth:`BaseNode.add_checkbox`,

        Args:
            name (str): node property name.

        Returns:
            NodeBaseWidget: embedded node widget.
        """
        return self.view.widgets.get(name)

    def add_custom_widget(self, widget, widget_type=None, tab=None):
        """
        Add a custom node widget into the node.

        see example :ref:`Embedding Custom Widgets`.

        Note:
            The ``value_changed`` signal from the added node widget is wired
            up to the :meth:`NodeObject.set_property` function.

        Args:
            widget (NodeBaseWidget): node widget class object.
            widget_type: widget flag to display in the
                :class:`NodeGraphQt.PropertiesBinWidget`
                (default: :attr:`NodeGraphQt.constants.NodePropWidgetEnum.HIDDEN`).
            tab (str): name of the widget tab to display in.
        """
        if not isinstance(widget, NodeBaseWidget):
            raise NodeWidgetError("'widget' must be an instance of a NodeBaseWidget")

        widget_type = widget_type or NodePropWidgetEnum.HIDDEN.value
        self.model.add_property(
            widget.get_name(),
            widget.get_value(),
            widget_type=widget_type,
            tab=tab,
        )
        widget.value_changed.connect(self.set_property)
        widget._node = self
        self.view.add_widget(widget)
        #: redraw node to address calls outside the "__init__" func.
        self.view.draw_node()

    def add_text_input(
        self, name, label="", text="", placeholder_text="", tooltip=None, tab=None
    ):
        """
        Creates a custom property with the :meth:`NodeObject.add_property`
        function and embeds a :class:`PySide2.QtWidgets.QLineEdit` widget
        into the node.

        Note:
            The ``value_changed`` signal from the added node widget is wired
            up to the :meth:`NodeObject.set_property` function.

        Args:
            name (str): name for the custom property.
            label (str): label to be displayed.
            text (str): pre-filled text.
            placeholder_text (str): placeholder text.
            tooltip (str): widget tooltip.
            tab (str): name of the widget tab to display in.
        """
        self.model.add_property(
            name,
            value=text,
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            widget_tooltip=tooltip,
            tab=tab,
        )
        widget = NodeLineEdit(self.view, name, label, text, placeholder_text)
        widget.setToolTip(tooltip or "")
        widget.value_changed.connect(self.set_property)
        self.view.add_widget(widget)
        #: redraw node to address calls outside the "__init__" func.
        self.view.draw_node()

    def hide_widget(self, name, push_undo=True):
        """
        Hide an embedded node widget.

        Args:
            name (str): node property name for the widget.
            push_undo (bool): register the command to the undo stack. (default: True)

        See Also:
            :meth:`BaseNode.add_custom_widget`,
            :meth:`BaseNode.show_widget`,
            :meth:`BaseNode.get_widget`
        """
        if not self.view.has_widget(name):
            return
        undo_cmd = NodeWidgetVisibleCmd(self, name, visible=False)
        if push_undo:
            self.graph.undo_stack().push(undo_cmd)
        else:
            undo_cmd.redo()

    def show_widget(self, name, push_undo=True):
        """
        Show an embedded node widget.

        Args:
            name (str): node property name for the widget.
            push_undo (bool): register the command to the undo stack. (default: True)

        See Also:
            :meth:`BaseNode.add_custom_widget`,
            :meth:`BaseNode.hide_widget`,
            :meth:`BaseNode.get_widget`
        """
        if not self.view.has_widget(name):
            return
        undo_cmd = NodeWidgetVisibleCmd(self, name, visible=True)
        if push_undo:
            self.graph.undo_stack().push(undo_cmd)
        else:
            undo_cmd.redo()

    def add_input(
        self,
        name="input",
        multi_input=False,
        display_name=True,
        color=None,
        locked=False,
    ):
        """
        Add input :class:`Port` to node.

        Warnings:
            Undo is NOT supported for this function.

        Args:
            name (str): name for the input port.
            multi_input (bool): allow port to have more than one connection.
            display_name (bool): display the port name on the node.
            color (tuple): initial port color (r, g, b) ``0-255``.
            locked (bool): locked state see :meth:`Port.set_locked`

        Returns:
            NodeGraphQt.Port: the created port object.
        """
        if name in self.inputs().keys():
            raise PortRegistrationError(f"port name '{name}' already registered.")

        port_args = [name, multi_input, display_name, locked]
        view = self.view.add_input(*port_args)

        if color:
            view.color = color
            view.border_color = [min([255, max([0, i + 80])]) for i in color]

        port = Port(node=self, view=view)
        port.dtype = PortTypeEnum.IN.value
        port.name = name
        port.display_name = display_name
        port.multi_connection = multi_input
        port.locked = locked
        self._inputs.append(port)
        self.model.inputs[port.name] = port
        return port

    def add_output(
        self,
        name="output",
        multi_output=True,
        display_name=True,
        color=None,
        locked=False,
    ):
        """
        Add output :class:`Port` to node.

        Warnings:
            Undo is NOT supported for this function.

        Args:
            name (str): name for the output port.
            multi_output (bool): allow port to have more than one connection.
            display_name (bool): display the port name on the node.
            color (tuple): initial port color (r, g, b) ``0-255``.
            locked (bool): locked state see :meth:`Port.set_locked`

        Returns:
            NodeGraphQt.Port: the created port object.
        """
        if name in self.outputs().keys():
            raise PortRegistrationError(f"port name '{name}' already registered.")

        port_args = [name, multi_output, display_name, locked]
        view = self.view.add_output(*port_args)

        if color:
            view.color = color
            view.border_color = [min([255, max([0, i + 80])]) for i in color]

        port = Port(node=self, view=view)
        port.dtype = PortTypeEnum.OUT.value
        port.name = name
        port.display_name = display_name
        port.multi_connection = multi_output
        port.locked = locked
        self._outputs.append(port)
        self.model.outputs[port.name] = port
        return port

    def get_input(self, port):
        """
        Get input port by the name or index.

        Args:
            port (str or int): port name or index.

        Returns:
            NodeGraphQt.Port: node port.
        """
        if isinstance(port, int):
            if port < len(self._inputs):
                return self._inputs[port]
        elif isinstance(port, str):
            return self.inputs().get(port, None)

    def get_output(self, port):
        """
        Get output port by the name or index.

        Args:
            port (str or int): port name or index.

        Returns:
            NodeGraphQt.Port: node port.
        """
        if isinstance(port, int):
            if port < len(self._outputs):
                return self._outputs[port]
        elif isinstance(port, str):
            return self.outputs().get(port, None)

    def delete_input(self, port):
        """
        Delete input port.

        Warnings:
            Undo is NOT supported for this function.

            You can only delete ports if :meth:`BaseNode.port_deletion_allowed`
            returns ``True`` otherwise a port error is raised see also
            :meth:`BaseNode.set_port_deletion_allowed`.

        Args:
            port (str or int): port name or index.
        """
        if type(port) in [int, str]:
            port = self.get_input(port)
            if port is None:
                return
        if not self.port_deletion_allowed():
            raise PortError(
                f"Port '{port.name}' can't be deleted on this node because "
                f"'ports_removable' is not enabled."
            )
        if port.locked:
            raise PortError("Error: Can't delete a port that is locked!")
        self._inputs.remove(port)
        self._model.inputs.pop(port.name)
        self._view.delete_input(port.view)
        # port.model.node = None
        self._view.draw_node()

    def delete_output(self, port):
        """
        Delete output port.

        Warnings:
            Undo is NOT supported for this function.

            You can only delete ports if :meth:`BaseNode.port_deletion_allowed`
            returns ``True`` otherwise a port error is raised see also
            :meth:`BaseNode.set_port_deletion_allowed`.

        Args:
            port (str or int): port name or index.
        """
        if type(port) in [int, str]:
            port = self.get_output(port)
            if port is None:
                return
        if not self.port_deletion_allowed():
            raise PortError(
                f"Port '{port.name}' can't be deleted on this node because "
                f"'ports_removable' is not enabled."
            )
        if port.locked:
            raise PortError("Error: Can't delete a port that is locked!")
        self._outputs.remove(port)
        self._model.outputs.pop(port.name)
        self._view.delete_output(port.view)
        # port.model.node = None
        self._view.draw_node()

    def set_port_deletion_allowed(self, mode=False):
        """
        Allow ports to be removable on this node.

        See Also:
            :meth:`BaseNode.port_deletion_allowed` and
            :meth:`BaseNode.set_ports`

        Args:
            mode (bool): true to allow.
        """
        self.model.port_deletion_allowed = mode

    def port_deletion_allowed(self):
        """
        Return true if ports can be deleted on this node.

        See Also:
            :meth:`BaseNode.set_port_deletion_allowed`

        Returns:
            bool: true if ports can be deleted.
        """
        return self.model.port_deletion_allowed

    def set_ports(self, port_data):
        """
        Create node input and output ports from serialized port data.

        Warnings:
            You can only use this function if the node has
            :meth:`BaseNode.port_deletion_allowed` is `True`
            see :meth:`BaseNode.set_port_deletion_allowed`

        Hint:
            example snippet of port data.

            .. highlight:: python
            .. code-block:: python

                {
                    'input_ports':
                        [{
                            'name': 'input',
                            'multi_connection': True,
                            'display_name': 'Input',
                            'locked': False
                        }],
                    'output_ports':
                        [{
                            'name': 'output',
                            'multi_connection': True,
                            'display_name': 'Output',
                            'locked': False
                        }]
                }

        Args:
            port_data(dict): port data.
        """
        if not self.port_deletion_allowed():
            raise PortError(
                "Ports cannot be set on this node because "
                '"set_port_deletion_allowed" is not enabled on this node.'
            )

        for port in self._inputs:
            self._view.delete_input(port.view)
            # port.model.node = None
        for port in self._outputs:
            self._view.delete_output(port.view)
            # port.model.node = None
        self._inputs = []
        self._outputs = []
        self._model.outputs = {}
        self._model.inputs = {}

        for port in port_data["input_ports"]:
            self.add_input(
                name=port["name"],
                multi_input=port["multi_connection"],
                display_name=port["display_name"],
                locked=port.get("locked") or False,
            )
        for port in port_data["output_ports"]:
            self.add_output(
                name=port["name"],
                multi_output=port["multi_connection"],
                display_name=port["display_name"],
                locked=port.get("locked") or False,
            )
        self._view.draw_node()

    def inputs(self):
        """
        Returns all the input ports from the node.

        Returns:
            dict: {<port_name>: <port_object>}
        """
        return {p.name: p for p in self._inputs}

    def input_ports(self):
        """
        Return all input ports.

        Returns:
            list[NodeGraphQt.Port]: node input ports.
        """
        return self._inputs

    def outputs(self):
        """
        Returns all the output ports from the node.

        Returns:
            dict: {<port_name>: <port_object>}
        """
        return {p.name: p for p in self._outputs}

    def output_ports(self):
        """
        Return all output ports.

        Returns:
            list[NodeGraphQt.Port]: node output ports.
        """
        return self._outputs

    def input(self, index):
        """
        Return the input port with the matching index.

        Args:
            index (int): index of the input port.

        Returns:
            NodeGraphQt.Port: port object.
        """
        return self._inputs[index]

    def set_input(self, index, port):
        """
        Creates a connection pipe to the targeted output :class:`Port`.

        Args:
            index (int): index of the port.
            port (NodeGraphQt.Port): port object.
        """
        src_port = self.input(index)
        src_port.connect_to(port)

    def output(self, index):
        """
        Return the output port with the matching index.

        Args:
            index (int): index of the output port.

        Returns:
            NodeGraphQt.Port: port object.
        """
        return self._outputs[index]

    def set_output(self, index, port):
        """
        Creates a connection pipe to the targeted input :class:`Port`.

        Args:
            index (int): index of the port.
            port (NodeGraphQt.Port): port object.
        """
        src_port = self.output(index)
        src_port.connect_to(port)

    def connected_input_nodes(self):
        """
        Returns all nodes connected from the input ports.

        Returns:
            dict: {<input_port>: <node_list>}
        """
        nodes = OrderedDict()
        for p in self.input_ports():
            nodes[p] = [cp.node for cp in p.get_connected_ports()]
        return nodes

    def connected_output_nodes(self):
        """
        Returns all nodes connected from the output ports.

        Returns:
            dict: {<output_port>: <node_list>}
        """
        nodes = OrderedDict()
        for p in self.output_ports():
            nodes[p] = [cp.node for cp in p.get_connected_ports()]
        return nodes

    def on_input_connected(self, in_port, out_port):
        """
        Callback triggered when a new pipe connection is made.

        *The default of this function does nothing re-implement if you require
        logic to run for this event.*

        Note:
            to work with undo & redo for this method re-implement
            :meth:`BaseNode.on_input_disconnected` with the reverse logic.

        Args:
            in_port (NodeGraphQt.Port): source input port from this node.
            out_port (NodeGraphQt.Port): output port that connected to this node.
        """
        return

    def on_input_disconnected(self, in_port, out_port):
        """
        Callback triggered when a pipe connection has been disconnected
        from a INPUT port.

        *The default of this function does nothing re-implement if you require
        logic to run for this event.*

        Note:
            to work with undo & redo for this method re-implement
            :meth:`BaseNode.on_input_connected` with the reverse logic.

        Args:
            in_port (NodeGraphQt.Port): source input port from this node.
            out_port (NodeGraphQt.Port): output port that was disconnected.
        """
        return

    def loaded(self):
        """
        This method is run after deserializing the Node.
        Useful for reconstructing custom widgets from properties.
        """
        pass
