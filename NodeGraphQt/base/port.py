from typing import List, DefaultDict
from collections import defaultdict
from pydantic import BaseModel, ConfigDict, Field

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


class PortModel(BaseModel):
    """
    Data dump for a port object.
    """

    node: NodeObject
    dtype: str = ""
    name: str = "port"
    display_name: bool = True
    multi_connection: bool = False
    visible: bool = True
    locked: bool = False
    connected_ports: DefaultDict[str, List[str]] = Field(
        default_factory=lambda: defaultdict(list)
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)


class Port:
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

    def __init__(self, node, port: "Port"):
        self.__view = port
        self.__model = PortModel(node=node)

    def __repr__(self):
        msg = f"{self.__class__.__name__}('{self.name}')"
        msg = f"<{msg} object at {hex(id(self))}>"
        return msg

    @property
    def view(self):
        """
        Returns the :class:`QtWidgets.QGraphicsItem` used in the scene.

        Returns:
            NodeGraphQt.qgraphics.port.PortItem: port item.
        """
        return self.__view

    @property
    def model(self):
        """
        Returns the port model.

        Returns:
            NodeGraphQt.base.model.PortModel: port model.
        """
        return self.__model

    @property
    def node(self):
        """
        Return the parent node.

        Returns:
            NodeGraphQt.BaseNode: parent node object.
        """
        return self.model.node

    @property
    def dtype(self):
        """
        Returns the port type.

        Port Types:
            - :attr:`NodeGraphQt.constants.IN_PORT` for input port
            - :attr:`NodeGraphQt.constants.OUT_PORT` for output port

        Returns:
            str: port connection type.
        """
        return self.model.dtype

    @property
    def name(self):
        """
        Returns the port name.

        Returns:
            str: port name.
        """
        return self.model.name

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
        port_name = self.name
        port_type = self.dtype
        node_type = self.node.dtype()

        ports = self.node._inputs + self.node._outputs
        if self not in ports:
            raise PortError(f"Node does not contain port '{self}'")

        data = (
            self.node._model._graph_model.accept_connection_types.get(node_type) or {}
        )
        accepted_types = data.get(port_type) or {}
        return accepted_types.get(port_name) or {}

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
        port_name = self.name
        port_type = self.dtype
        node_type = self.node.dtype()

        ports = self.node._inputs + self.node._outputs
        if self not in ports:
            raise PortError(f"Node does not contain port '{self}'")

        data = (
            self.node._model._graph_model.reject_connection_types.get(node_type) or {}
        )
        rejected_types = data.get(port_type) or {}
        return rejected_types.get(port_name) or {}

    @property
    def color(self):
        return self.__view.color

    @color.setter
    def color(self, color=(0, 0, 0, 255)):
        self.__view.color = color

    @property
    def border_color(self):
        return self.__view.border_color

    @border_color.setter
    def border_color(self, color=(0, 0, 0, 255)):
        self.__view.border_color = color

    def multi_connection(self):
        """
        Returns if the ports is a single connection or not.

        Returns:
            bool: false if port is a single connection port
        """
        return self.model.multi_connection

    def visible(self):
        """
        Port visible in the node graph.

        Returns:
            bool: true if visible.
        """
        return self.model.visible

    def set_visible(self, visible=True, push_undo=True):
        """
        Sets weather the port should be visible or not.

        Args:
            visible (bool): true if visible.
            push_undo (bool): register the command to the undo stack. (default: True)
        """

        # prevent signals from causing an infinite loop.
        if visible == self.visible():
            return

        undo_cmd = PortVisibleCmd(self, visible)
        if push_undo:
            undo_stack = self.node.graph.undo_stack()
            undo_stack.push(undo_cmd)
        else:
            undo_cmd.redo()

    def locked(self):
        """
        Returns the locked state.

        If ports are locked then new pipe connections can't be connected
        and current connected pipes can't be disconnected.

        Returns:
            bool: true if locked.
        """
        return self.model.locked

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

    def set_locked(self, state=False, connected_ports=True, push_undo=True):
        """
        Sets the port locked state. When locked pipe connections can't be
        connected or disconnected from this port.

        Args:
            state (Bool): port lock state.
            connected_ports (Bool): apply to lock state to connected ports.
            push_undo (bool): register the command to the undo stack. (default: True)
        """

        # prevent signals from causing an infinite loop.
        if state == self.locked():
            return

        graph = self.node.graph
        undo_stack = graph.undo_stack()
        if state:
            undo_cmd = PortLockedCmd(self)
        else:
            undo_cmd = PortUnlockedCmd(self)
        if push_undo:
            undo_stack.push(undo_cmd)
        else:
            undo_cmd.redo()
        if connected_ports:
            for port in self.connected_ports():
                port.set_locked(state, connected_ports=False, push_undo=push_undo)

    def connected_ports(self):
        """
        Returns all connected ports.

        Returns:
            list[NodeGraphQt.Port]: list of connected ports.
        """
        ports = []
        graph = self.node.graph
        for node_id, port_names in self.model.connected_ports.items():
            for port_name in port_names:
                node = graph.get_node_by_id(node_id)
                if self.dtype == PortTypeEnum.IN.value:
                    ports.append(node.outputs()[port_name])
                elif self.dtype == PortTypeEnum.OUT.value:
                    ports.append(node.inputs()[port_name])
        return ports

    def connect_to(self, port=None, push_undo=True, emit_signal=True):
        """
        Create connection to the specified port and emits the
        :attr:`NodeGraph.port_connected` signal from the parent node graph.

        Args:
            port (NodeGraphQt.Port): port object.
            push_undo (bool): register the command to the undo stack. (default: True)
            emit_signal (bool): emit the port connection signals. (default: True)
        """
        if not port:
            return

        if self in port.connected_ports():
            return

        if self.locked() or port.locked():
            name = [p.name for p in [self, port] if p.locked()][0]
            raise PortError(f"Can't connect port because '{name}' is locked.")

        # validate accept connection.
        node_type = self.node.dtype()
        accepted_types = port.accepted_port_types.get(node_type)
        if accepted_types:
            accepted_pnames = accepted_types.get(self.dtype) or set([])
            if self.name not in accepted_pnames:
                return
        node_type = port.node.dtype
        accepted_types = self.accepted_port_types.get(node_type)
        if accepted_types:
            accepted_pnames = accepted_types.get(port.dtype) or set([])
            if port.name not in accepted_pnames:
                return

        # validate reject connection.
        node_type = self.node.dtype()
        rejected_types = port.rejected_port_types.get(node_type)
        if rejected_types:
            rejected_pnames = rejected_types.get(self.dtype) or set([])
            if self.name in rejected_pnames:
                return
        node_type = port.node.dtype
        rejected_types = self.rejected_port_types.get(node_type)
        if rejected_types:
            rejected_pnames = rejected_types.get(port.dtype) or set([])
            if port.name in rejected_pnames:
                return

        # make the connection from here.
        graph = self.node.graph
        viewer = graph.viewer()

        if push_undo:
            undo_stack = graph.undo_stack()
            undo_stack.beginMacro("connect port")

        pre_conn_port = None
        src_conn_ports = self.connected_ports()
        if not self.multi_connection() and src_conn_ports:
            pre_conn_port = src_conn_ports[0]

        if not port:
            if pre_conn_port:
                if push_undo:
                    undo_stack.push(PortDisconnectedCmd(self, port, emit_signal))
                    undo_stack.push(NodeInputDisconnectedCmd(self, port))
                    undo_stack.endMacro()
                else:
                    PortDisconnectedCmd(self, port, emit_signal).redo()
                    NodeInputDisconnectedCmd(self, port).redo()
            return

        if graph.acyclic() and viewer.acyclic_check(self.view, port.view):
            if pre_conn_port:
                if push_undo:
                    undo_stack.push(
                        PortDisconnectedCmd(self, pre_conn_port, emit_signal)
                    )
                    undo_stack.push(NodeInputDisconnectedCmd(self, pre_conn_port))
                    undo_stack.endMacro()
                else:
                    PortDisconnectedCmd(self, pre_conn_port, emit_signal).redo()
                    NodeInputDisconnectedCmd(self, pre_conn_port).redo()
                return

        trg_conn_ports = port.connected_ports()
        if not port.multi_connection() and trg_conn_ports:
            dettached_port = trg_conn_ports[0]
            if push_undo:
                undo_stack.push(PortDisconnectedCmd(port, dettached_port, emit_signal))
                undo_stack.push(NodeInputDisconnectedCmd(port, dettached_port))
            else:
                PortDisconnectedCmd(port, dettached_port, emit_signal).redo()
                NodeInputDisconnectedCmd(port, dettached_port).redo()
        if pre_conn_port:
            if push_undo:
                undo_stack.push(PortDisconnectedCmd(self, pre_conn_port, emit_signal))
                undo_stack.push(NodeInputDisconnectedCmd(self, pre_conn_port))
            else:
                PortDisconnectedCmd(self, pre_conn_port, emit_signal).redo()
                NodeInputDisconnectedCmd(self, pre_conn_port).redo()

        if push_undo:
            undo_stack.push(PortConnectedCmd(self, port, emit_signal))
            undo_stack.push(NodeInputConnectedCmd(self, port))
            undo_stack.endMacro()
        else:
            PortConnectedCmd(self, port, emit_signal).redo()
            NodeInputConnectedCmd(self, port).redo()

    def disconnect_from(self, port=None, push_undo=True, emit_signal=True):
        """
        Disconnect from the specified port and emits the
        :attr:`NodeGraph.port_disconnected` signal from the parent node graph.

        Args:
            port (NodeGraphQt.Port): port object.
            push_undo (bool): register the command to the undo stack. (default: True)
            emit_signal (bool): emit the port connection signals. (default: True)
        """
        if not port:
            return

        if self.locked() or port.locked():
            name = [p.name for p in [self, port] if p.locked()][0]
            raise PortError(f"Can't disconnect port because '{name}' is locked.")

        graph = self.node.graph
        if push_undo:
            graph.undo_stack().beginMacro("disconnect port")
            graph.undo_stack().push(PortDisconnectedCmd(self, port, emit_signal))
            graph.undo_stack().push(NodeInputDisconnectedCmd(self, port))
            graph.undo_stack().endMacro()
        else:
            PortDisconnectedCmd(self, port, emit_signal).redo()
            NodeInputDisconnectedCmd(self, port).redo()

    def clear_connections(self, push_undo=True, emit_signal=True):
        """
        Disconnect from all port connections and emit the
        :attr:`NodeGraph.port_disconnected` signals from the node graph.

        See Also:
            :meth:`Port.disconnect_from`,
            :meth:`Port.connect_to`,
            :meth:`Port.connected_ports`

        Args:
            push_undo (bool): register the command to the undo stack. (default: True)
            emit_signal (bool): emit the port connection signals. (default: True)
        """
        if self.locked():
            err = 'Can\'t clear connections because port "{}" is locked.'
            raise PortError(err.format(self.name))

        if not self.connected_ports():
            return

        if push_undo:
            graph = self.node.graph
            undo_stack = graph.undo_stack()
            undo_stack.beginMacro('"{}" clear connections')
            for cp in self.connected_ports():
                self.disconnect_from(cp, emit_signal=emit_signal)
            undo_stack.endMacro()
            return

        for cp in self.connected_ports():
            self.disconnect_from(cp, push_undo=False, emit_signal=emit_signal)
