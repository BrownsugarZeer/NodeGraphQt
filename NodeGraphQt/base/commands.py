from PySide6 import QtGui

from NodeGraphQt.constants import PortTypeEnum


class PropertyChangedCmd(QtGui.QUndoCommand):
    """
    Node property changed command.

    Args:
        node (NodeGraphQt.NodeObject): node.
        name (str): node property name.
        value (object): node property value.
    """

    def __init__(self, node, name, value):
        super().__init__()
        self.setText(f"property '{node.view.name}:{name}'")
        self.node = node
        self.name = name
        self.old_val = node.model.get_property(name)
        self.new_val = value

    def set_node_property(self, name, value):
        """
        updates the node view and model.
        """
        # set model data.
        model = self.node.model
        model.set_property(name, value)

        # set view data.
        view = self.node.view

        # view widgets.
        if hasattr(view, "widgets") and name in view.widgets.keys():
            # check if previous value is identical to current value,
            # prevent signals from causing an infinite loop.
            if view.widgets[name].get_value() is not value:
                view.widgets[name].set_value(value)

        # view properties.
        if name in view.properties.keys():
            # remap "pos" to "xy_pos" node view has pre-existing pos method.
            if name == "pos":
                name = "xy_pos"
            setattr(view, name, value)

        # emit property changed signal.
        graph = self.node.graph
        graph.property_changed.emit(self.node, self.name, value)

    def undo(self):
        if self.old_val is not self.new_val:
            self.set_node_property(self.name, self.old_val)

    def redo(self):
        if self.old_val is not self.new_val:
            self.set_node_property(self.name, self.new_val)


class NodeVisibleCmd(QtGui.QUndoCommand):
    """
    Node visibility changed command.

    Args:
        node (NodeGraphQt.NodeObject): node.
        visible (bool): node visible value.
    """

    def __init__(self, node, visible):
        super().__init__()
        self.node = node
        self.visible = visible
        self.selected = self.node.selected()

    def set_node_visible(self, visible):
        model = self.node.model
        model.set_property("visible", visible)

        node_view = self.node.view
        node_view.visible = visible

        # redraw the connected pipes in the scene.
        # TODO: type_hint: NodeGraphQt.PortModel
        ports = node_view.inputs + node_view.outputs
        for port in ports:
            for pipe in port.view.connected_pipes:
                pipe.update()

        # restore the node selected state.
        if self.selected != node_view.isSelected():
            node_view.setSelected(model.selected)

        # emit property changed signal.
        graph = self.node.graph
        graph.property_changed.emit(self.node, "visible", visible)

    def undo(self):
        self.set_node_visible(not self.visible)

    def redo(self):
        self.set_node_visible(self.visible)


class NodeWidgetVisibleCmd(QtGui.QUndoCommand):
    """
    Node widget visibility command.

    Args:
        node (NodeGraphQt.NodeObject): node object.
        name (str): node widget name.
        visible (bool): initial visibility state.
    """

    def __init__(self, node, name, visible):
        super().__init__()
        label = "show" if visible else "hide"
        self.setText(f"{label} node widget '{name}'")
        self.view = node.view
        self.node_widget = self.view.get_widget(name)
        self.visible = visible

    def undo(self):
        self.node_widget.setVisible(not self.visible)
        self.view.draw_node()

    def redo(self):
        self.node_widget.setVisible(self.visible)
        self.view.draw_node()


class NodeMovedCmd(QtGui.QUndoCommand):
    """
    Node moved command.

    Args:
        node (NodeGraphQt.NodeObject): node.
        pos (tuple(float, float)): new node position.
        prev_pos (tuple(float, float)): previous node position.
    """

    def __init__(self, node, pos, prev_pos):
        super().__init__()
        self.node = node
        self.pos = pos
        self.prev_pos = prev_pos

    def undo(self):
        self.node.view.xy_pos = self.prev_pos
        self.node.model.pos = self.prev_pos

    def redo(self):
        if self.pos == self.prev_pos:
            return
        self.node.view.xy_pos = self.pos
        self.node.model.pos = self.pos


class NodeAddedCmd(QtGui.QUndoCommand):
    """
    Node added command.

    Args:
        graph (NodeGraphQt.NodeGraph): node graph.
        node (NodeGraphQt.NodeObject): node.
        pos (tuple(float, float)): initial node position (optional).
        emit_signal (bool): emit node creation signals. (default: True)
    """

    def __init__(self, graph, node, pos=None, emit_signal=True):
        super().__init__()
        self.setText("added node")
        self.graph = graph
        self.node = node
        self.pos = pos
        self.emit_signal = emit_signal

    def undo(self):
        node_id = self.node.id
        self.pos = self.pos or self.node.view.xy_pos
        self.graph.model.nodes.pop(self.node.id)
        self.node.view.delete()

        if self.emit_signal:
            self.graph.nodes_deleted.emit([node_id])

    def redo(self):
        # TODO: add the node
        self.graph.model.nodes[self.node.id] = self.node
        self.graph.viewer().add_node(self.node.view, self.pos)

        # node width & height is calculated when it's added to the scene,
        # so we have to update the node model here.
        self.node.model.width = self.node.view.width
        self.node.model.height = self.node.view.height

        if self.emit_signal:
            self.graph.node_created.emit(self.node)


class NodesRemovedCmd(QtGui.QUndoCommand):
    """
    Node deleted command.

    Args:
        graph (NodeGraphQt.NodeGraph): node graph.
        nodes (list[NodeGraphQt.BaseNode or NodeGraphQt.NodeObject]): nodes.
        emit_signal (bool): emit node deletion signals. (default: True)
    """

    def __init__(self, graph, nodes, emit_signal=True):
        super().__init__()
        self.setText("deleted node(s)")
        self.graph = graph
        self.nodes = nodes
        self.emit_signal = emit_signal

    def undo(self):
        for node in self.nodes:
            # TODO: add the node
            self.graph.model.nodes[node.id] = node
            self.graph.scene().addItem(node.view)

            if self.emit_signal:
                self.graph.node_created.emit(node)

    def redo(self):
        node_ids = []
        for node in self.nodes:
            node_ids.append(node.id)
            self.graph.model.nodes.pop(node.id)
            node.view.delete()

        if self.emit_signal:
            self.graph.nodes_deleted.emit(node_ids)


class NodeInputConnectedCmd(QtGui.QUndoCommand):
    """
    "BaseNode.on_input_connected()" command.

    Args:
        src_port (NodeGraphQt.Port): source port.
        trg_port (NodeGraphQt.Port): target port.
    """

    def __init__(self, src_port, trg_port):
        super().__init__()
        if src_port.view.port_type == PortTypeEnum.IN.value:
            self.source = src_port
            self.target = trg_port
        else:
            self.source = trg_port
            self.target = src_port

    def undo(self):
        node = self.source.node
        node.on_input_disconnected(self.source, self.target)

    def redo(self):
        node = self.source.node
        node.on_input_connected(self.source, self.target)


class NodeInputDisconnectedCmd(QtGui.QUndoCommand):
    """
    Node "on_input_disconnected()" command.

    Args:
        src_port (NodeGraphQt.Port): source port.
        trg_port (NodeGraphQt.Port): target port.
    """

    def __init__(self, src_port, trg_port):
        super().__init__()
        # TODO: type_hint: NodeGraphQt.PortModel
        if src_port.view.port_type == PortTypeEnum.IN.value:
            self.source = src_port
            self.target = trg_port
        else:
            self.source = trg_port
            self.target = src_port

    def undo(self):
        node = self.source.node
        node.on_input_connected(self.source, self.target)

    def redo(self):
        node = self.source.node
        node.on_input_disconnected(self.source, self.target)


class PortConnectedCmd(QtGui.QUndoCommand):
    """
    Port connected command.

    Args:
        src_port (NodeGraphQt.Port): source port.
        trg_port (NodeGraphQt.Port): target port.
        emit_signal (bool): emit port connection signals.
    """

    def __init__(self, src_port, trg_port, emit_signal):
        super().__init__()
        self.source = src_port
        self.target = trg_port
        self.emit_signal = emit_signal

    def undo(self):
        src_model = self.source
        trg_model = self.target
        src_id = self.source.node.id
        trg_id = self.target.node.id

        port_names = src_model.connected_ports.get(trg_id)
        if port_names is []:
            del src_model.connected_ports[trg_id]
        # TODO: type_hint: NodeGraphQt.PortModel
        if port_names and self.target.view.name in port_names:
            port_names.remove(self.target.view.name)

        port_names = trg_model.connected_ports.get(src_id)
        if port_names is []:
            del trg_model.connected_ports[src_id]
        # TODO: type_hint: NodeGraphQt.PortModel
        if port_names and self.source.view.name in port_names:
            port_names.remove(self.source.view.name)

        self.source.view.disconnect_from(self.target.view)

        # emit "port_disconnected" signal from the parent graph.
        if self.emit_signal:
            ports = {p.view.port_type: p for p in [self.source, self.target]}
            graph = self.source.node.graph
            graph.port_disconnected.emit(
                ports[PortTypeEnum.IN.value], ports[PortTypeEnum.OUT.value]
            )

    def redo(self):
        src_model = self.source
        trg_model = self.target
        src_id = self.source.node.id
        trg_id = self.target.node.id

        # TODO: type_hint: NodeGraphQt.PortModel
        src_model.connected_ports[trg_id].append(self.target.view.name)
        trg_model.connected_ports[src_id].append(self.source.view.name)

        self.source.view.connect_to(self.target.view)

        # emit "port_connected" signal from the parent graph.
        # TODO: type_hint: NodeGraphQt.PortModel
        if self.emit_signal:
            ports = {p.view.port_type: p for p in [self.source, self.target]}
            graph = self.source.node.graph
            graph.port_connected.emit(
                ports[PortTypeEnum.IN.value], ports[PortTypeEnum.OUT.value]
            )


class PortDisconnectedCmd(QtGui.QUndoCommand):
    """
    Port disconnected command.

    Args:
        src_port (NodeGraphQt.Port): source port.
        trg_port (NodeGraphQt.Port): target port.
        emit_signal (bool): emit port connection signals.
    """

    def __init__(self, src_port, trg_port, emit_signal):
        super().__init__()
        self.source = src_port
        self.target = trg_port
        self.emit_signal = emit_signal

    def undo(self):
        src_model = self.source
        trg_model = self.target
        src_id = self.source.node.id
        trg_id = self.target.node.id

        # TODO: type_hint: NodeGraphQt.PortModel
        src_model.connected_ports[trg_id].append(self.target.view.name)
        trg_model.connected_ports[src_id].append(self.source.view.name)

        self.source.view.connect_to(self.target.view)

        # emit "port_connected" signal from the parent graph.
        if self.emit_signal:
            ports = {p.view.port_type: p for p in [self.source, self.target]}
            graph = self.source.node.graph
            graph.port_connected.emit(
                ports[PortTypeEnum.IN.value], ports[PortTypeEnum.OUT.value]
            )

    def redo(self):
        src_model = self.source  # TODO: type_hint: NodeGraphQt.PortModel
        trg_model = self.target  # TODO: type_hint: NodeGraphQt.PortModel
        src_id = self.source.node.id
        trg_id = self.target.node.id

        port_names = src_model.connected_ports.get(trg_id)
        if port_names is []:
            del src_model.connected_ports[trg_id]
        # TODO: type_hint: NodeGraphQt.PortModel
        if port_names and self.target.view.name in port_names:
            port_names.remove(self.target.view.name)

        port_names = trg_model.connected_ports.get(src_id)
        if port_names is []:
            del trg_model.connected_ports[src_id]
        # TODO: type_hint: NodeGraphQt.PortModel
        if port_names and self.source.view.name in port_names:
            port_names.remove(self.source.view.name)

        self.source.view.disconnect_from(self.target.view)

        # emit "port_disconnected" signal from the parent graph.
        if self.emit_signal:
            # TODO: type_hint: NodeGraphQt.PortModel
            ports = {p.view.port_type: p for p in [self.source, self.target]}
            graph = self.source.node.graph
            graph.port_disconnected.emit(
                ports[PortTypeEnum.IN.value], ports[PortTypeEnum.OUT.value]
            )


class PortLockedCmd(QtGui.QUndoCommand):
    """
    Port locked command.

    Args:
        port (NodeGraphQt.Port): node port.
    """

    def __init__(self, port):
        super().__init__()
        # TODO: type_hint: NodeGraphQt.PortModel
        self.setText(f"lock port '{port.view.name}'")
        self.port = port

    def undo(self):
        self.port.view.locked = False

    def redo(self):
        self.port.view.locked = True


class PortUnlockedCmd(QtGui.QUndoCommand):
    """
    Port unlocked command.

    Args:
        port (NodeGraphQt.Port): node port.
    """

    def __init__(self, port):
        super().__init__()
        self.setText(f"unlock port '{port.view.name}'")
        self.port = port

    def undo(self):
        self.port.view.locked = True

    def redo(self):
        self.port.view.locked = False


class PortVisibleCmd(QtGui.QUndoCommand):
    """
    Port visibility command.

    Args:
        port (NodeGraphQt.Port): node port.
    """

    def __init__(self, port, visible):
        super().__init__()
        self.port = port
        self.visible = visible
        if visible:
            self.setText(f"show port {self.port.view.name}")
        else:
            self.setText(f"hide port {self.port.view.name}")

    def set_visible(self, visible):
        self.port.visible = visible
        self.port.view.setVisible(visible)
        node_view = self.port.node.view
        text_item = None
        if self.port.view.port_type == PortTypeEnum.IN.value:
            text_item = node_view.get_input_text_item(self.port.view)
        elif self.port.view.port_type == PortTypeEnum.OUT.value:
            text_item = node_view.get_output_text_item(self.port.view)
        if text_item:
            text_item.setVisible(visible)

        node_view.draw_node()

        # redraw the connected pipes in the scene.
        for port in node_view.inputs + node_view.outputs:
            for pipe in port.connected_pipes:
                pipe.update()

    def undo(self):
        self.set_visible(not self.visible)

    def redo(self):
        self.set_visible(self.visible)
