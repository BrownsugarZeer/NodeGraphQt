from uuid import uuid4
from typing import List, DefaultDict
from collections import defaultdict
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from NodeGraphQt.base.commands import (
    PortConnectedCmd,
    PortDisconnectedCmd,
    PortLockedCmd,
    PortUnlockedCmd,
    PortVisibleCmd,
    NodeInputConnectedCmd,
    NodeInputDisconnectedCmd,
)

from NodeGraphQt.nodes.base_model import NodeObject
from NodeGraphQt.constants import PortTypeEnum
from NodeGraphQt.errors import PortError
from NodeGraphQt.ports.base_item import PortItem


class PortModel(BaseModel):
    """
    The ``Port`` class is used for connecting one node to another.

    .. inheritance-diagram:: NodeGraphQt.Port

    .. image:: _images/port.png
        :width: 50%

    See Also:
        For adding a ports into a node see:
        :meth:`BaseNode.add_input`, :meth:`BaseNode.add_output`

    Args:
        node (NodeGraphQt.NodeObject): parent node.
        port (PortItem): graphic item used for drawing.
    """

    _uuid: str = PrivateAttr(
        default_factory=lambda: uuid4().hex,
    )
    view: "PortItem" = Field(
        description="Returns the :class:`QtWidgets.QGraphicsItem` used in the scene.",
    )
    node: NodeObject = Field(
        # NOTE: Actually, this is a NodeGraphQt.BaseNode
        description="Parent node object"
    )
    visible: bool = Field(
        default=True, description="Whether the port is visible in the node graph or not"
    )
    connected_ports: DefaultDict[str, List[str]] = Field(
        default_factory=lambda: defaultdict(list)
    )
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __hash__(self):
        return hash(self._uuid)

    def __repr__(self):
        msg = f"{self.__class__.__name__}('{self.view.name}')"
        msg = f"<{msg} object at {hex(id(self))}>"
        return msg

    @property
    def accepted_port_types(self):
        """
        Returns a dictionary of connection constrains of the port types
        that allow for a pipe connection to this node.

        See Also:
            :meth:`NodeGraphQt.BaseNode.accepted_port_types`

        Returns:
            dict: {<node_type>: {<port_type>: [<port_name>]}}
        """
        port_name = self.view.name
        port_type = self.view.port_type
        node_type = self.node.identifier

        ports = self.node._inputs + self.node._outputs
        if self not in ports:
            raise PortError(f"Node does not contain port '{self}'")

        data = (
            self.node._model._graph_model.accept_connection_types.get(node_type) or {}
        )
        accepted_types = data.get(port_type, {})
        return accepted_types.get(port_name, {})

    @property
    def rejected_port_types(self):
        """
        Returns a dictionary of connection constrains of the port types
        that are NOT allowed for a pipe connection to this node.

        See Also:
            :meth:`NodeGraphQt.BaseNode.rejected_port_types`

        Returns:
            dict: {<node_type>: {<port_type>: [<port_name>]}}
        """
        port_name = self.view.name
        port_type = self.view.port_type
        node_type = self.node.identifier

        ports = self.node._inputs + self.node._outputs
        if self not in ports:
            raise PortError(f"Node does not contain port '{self}'")

        data = (
            self.node._model._graph_model.reject_connection_types.get(node_type) or {}
        )
        rejected_types = data.get(port_type, {})
        return rejected_types.get(port_name, {})

    def set_visible(self, visible=True):
        """
        Sets weather the port should be visible or not.

        Args:
            visible (bool): true if visible.
        """

        # prevent signals from causing an infinite loop.
        if visible == self.visible:
            return

        undo_cmd = PortVisibleCmd(self, visible)
        undo_stack = self.node.graph.undo_stack()
        undo_stack.push(undo_cmd)

    def lock(self):
        """
        Lock the port so new pipe connections can't be connected and
        current connected pipes can't be disconnected.

        This is the same as calling :meth:`Port.set_locked` with the arg
        set to ``True``
        """
        self.set_locked(True, connected_ports=True)

    def unlock(self):
        """
        Unlock the port so new pipe connections can be connected and
        existing connected pipes can be disconnected.

        This is the same as calling :meth:`Port.set_locked` with the arg
        set to ``False``
        """
        self.set_locked(False, connected_ports=True)

    def set_locked(self, state=False, connected_ports=True):
        """
        Sets the port locked state. When locked pipe connections can't be
        connected or disconnected from this port.

        Args:
            state (Bool): port lock state.
            connected_ports (Bool): apply to lock state to connected ports.
        """

        # prevent signals from causing an infinite loop.
        if state == self.view.locked:
            return

        graph = self.node.graph
        undo_stack = graph.undo_stack()
        if state:
            undo_cmd = PortLockedCmd(self)
        else:
            undo_cmd = PortUnlockedCmd(self)

        undo_stack.push(undo_cmd)

        if connected_ports:
            for port in self.get_connected_ports():
                port.set_locked(state, connected_ports=False)

    def get_connected_ports(self):
        """
        Returns all connected ports.

        Returns:
            list[NodeGraphQt.Port]: list of connected ports.
        """
        ports = []
        graph = self.node.graph
        for node_id, port_names in self.connected_ports.items():
            for port_name in port_names:
                node = graph.get_node_by_id(node_id)
                if self.view.port_type == PortTypeEnum.IN.value:
                    ports.append(node.outputs()[port_name])
                elif self.view.port_type == PortTypeEnum.OUT.value:
                    ports.append(node.inputs()[port_name])
        return ports

    def connect_to(self, port=None, emit_signal=True):
        """
        Create connection to the specified port and emits the
        :attr:`NodeGraph.port_connected` signal from the parent node graph.

        Args:
            port (NodeGraphQt.Port): port object.
            emit_signal (bool): emit the port connection signals. (default: True)
        """
        if not port and self in port.get_connected_ports():
            return

        if self.view.locked or port.view.locked:
            name = [p.view.name for p in [self, port] if p.view.locked][0]
            raise PortError(f"Can't connect port because '{name}' is locked.")

        def is_valid_connection(port_a, port_b):
            accepted_types = port_a.accepted_port_types.get(port_b.node.identifier)
            rejected_types = port_a.rejected_port_types.get(port_b.node.identifier)
            if None in [accepted_types, rejected_types]:
                return

            accepted_names = accepted_types.get(port_b.view.port_type, {})
            rejected_names = rejected_types.get(port_b.view.port_type, {})
            if (
                port_b.view.name not in accepted_names
                or port_b.view.name in rejected_names
            ):
                return

        is_valid_connection(self, port)
        is_valid_connection(port, self)

        graph = self.node.graph
        viewer = graph.viewer()
        undo_stack = graph.undo_stack()
        undo_stack.beginMacro("connect port")

        pre_conn_port = (
            self.get_connected_ports()[0]
            if not self.view.multi_connection and self.get_connected_ports()
            else None
        )

        def handle_disconnection(cmd_class, src_port, tgt_port):
            undo_stack.push(cmd_class(src_port, tgt_port, emit_signal))

        if not port and pre_conn_port:
            handle_disconnection(PortDisconnectedCmd, self, pre_conn_port)
            handle_disconnection(NodeInputDisconnectedCmd, self, pre_conn_port)
            undo_stack.endMacro()
            return

        if (
            graph.acyclic
            and viewer.acyclic_check(self.view, port.view)
            and pre_conn_port
        ):
            handle_disconnection(PortDisconnectedCmd, self, pre_conn_port)
            handle_disconnection(NodeInputDisconnectedCmd, self, pre_conn_port)
            undo_stack.endMacro()
            return

        dettached_port = (
            port.get_connected_ports()[0]
            if not port.view.multi_connection and port.get_connected_ports()
            else None
        )
        if dettached_port:
            handle_disconnection(PortDisconnectedCmd, port, dettached_port)
            handle_disconnection(NodeInputDisconnectedCmd, port, dettached_port)

        if pre_conn_port:
            handle_disconnection(PortDisconnectedCmd, self, pre_conn_port)
            handle_disconnection(NodeInputDisconnectedCmd, self, pre_conn_port)

        undo_stack.push(PortConnectedCmd(self, port, emit_signal))
        undo_stack.push(NodeInputConnectedCmd(self, port))
        undo_stack.endMacro()

    def disconnect_from(self, port=None, emit_signal=True):
        """
        Disconnect from the specified port and emits the
        :attr:`NodeGraph.port_disconnected` signal from the parent node graph.

        Args:
            port (NodeGraphQt.Port): port object.
            emit_signal (bool): emit the port connection signals. (default: True)
        """
        if not port:
            return

        if self.view.locked or port.view.locked:
            name = [p.view.name for p in [self, port] if p.view.locked][0]
            raise PortError(f"Can't disconnect port because '{name}' is locked.")

        graph = self.node.graph
        graph.undo_stack().beginMacro("disconnect port")
        graph.undo_stack().push(PortDisconnectedCmd(self, port, emit_signal))
        graph.undo_stack().push(NodeInputDisconnectedCmd(self, port))
        graph.undo_stack().endMacro()

    def clear_connections(self, emit_signal=True):
        """
        Disconnect from all port connections and emit the
        :attr:`NodeGraph.port_disconnected` signals from the node graph.

        See Also:
            :meth:`Port.disconnect_from`,
            :meth:`Port.connect_to`,
            :meth:`Port.connected_ports`

        Args:
            emit_signal (bool): emit the port connection signals. (default: True)
        """
        if self.view.locked:
            err = 'Can\'t clear connections because port "{}" is locked.'
            raise PortError(err.format(self.view.name))

        if not self.get_connected_ports():
            return

        graph = self.node.graph
        undo_stack = graph.undo_stack()
        undo_stack.beginMacro('"{}" clear connections')
        for cp in self.get_connected_ports():
            self.disconnect_from(cp, emit_signal=emit_signal)
        undo_stack.endMacro()
