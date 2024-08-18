import json
from typing import List, Dict, Tuple, Optional
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict
from NodeGraphQt.base.commands import PropertyChangedCmd
from NodeGraphQt.constants import (
    LayoutDirectionEnum,
    NodePropWidgetEnum,
)
from NodeGraphQt.errors import NodePropertyError
from icecream import ic

# from NodeGraphQt.base.model import NodeModel
from NodeGraphQt.qgraphics.node_base import NodeItem
from NodeGraphQt.base.model import NodeGraphModel

from NodeGraphQt.constants import NodePropWidgetEnum


class NodeModel(BaseModel):
    """
    Data dump for a node object.
    """

    dtype: Optional["NodeObject"] = None
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str = "node"
    border_color: Tuple[int, int, int, int] = (74, 84, 85, 255)
    text_color: Tuple[int, int, int, int] = (255, 255, 255, 180)
    disabled: bool = False
    selected: bool = False
    width: float = 100.0
    height: float = 80.0
    pos: List[float] = [0.0, 0.0]
    layout_direction: int = LayoutDirectionEnum.HORIZONTAL.value

    visible: bool = True
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # BaseNode attrs.
    inputs: Dict = {}
    outputs: Dict = {}
    port_deletion_allowed: bool = False

    # Custom
    _custom_prop: Dict = {}

    # node graph model set at node added time.
    _graph_model: Optional[NodeGraphModel] = None

    # store the property attributes.
    # (deleted when node is added to the graph)
    _TEMP_property_attrs: Dict = {}

    # temp store the property widget types.
    # (deleted when node is added to the graph)
    _TEMP_property_widget_types: Dict = {
        "dtype": NodePropWidgetEnum.QLABEL.value,
        "id": NodePropWidgetEnum.QLABEL.value,
        "name": NodePropWidgetEnum.QLINE_EDIT.value,
        "border_color": NodePropWidgetEnum.COLOR_PICKER.value,
        "text_color": NodePropWidgetEnum.COLOR_PICKER.value,
        "disabled": NodePropWidgetEnum.QCHECK_BOX.value,
        "selected": NodePropWidgetEnum.HIDDEN.value,
        "width": NodePropWidgetEnum.HIDDEN.value,
        "height": NodePropWidgetEnum.HIDDEN.value,
        "pos": NodePropWidgetEnum.HIDDEN.value,
        "layout_direction": NodePropWidgetEnum.HIDDEN.value,
        "inputs": NodePropWidgetEnum.HIDDEN.value,
        "outputs": NodePropWidgetEnum.HIDDEN.value,
    }

    # temp store connection constrains.
    # (deleted when node is added to the graph)
    _TEMP_accept_connection_types: Dict = {}
    _TEMP_reject_connection_types: Dict = {}

    def __repr__(self):
        msg = f"{self.__class__.__name__}('{self.name}')"
        msg = f"<{msg} object at {self.id}>"
        return msg

    def add_property(
        self,
        name,
        value,
        items=None,
        range=None,
        widget_type=None,
        widget_tooltip=None,
        tab=None,
    ):
        """
        add custom property or raises an error if the property name is already
        taken.

        Args:

            name (str): name of the property.
            value (object): data.
            items (list[str]): items used by widget type NODE_PROP_QCOMBO.
            range (tuple): min, max values used by NODE_PROP_SLIDER.
            widget_type (int): widget type flag.
            widget_tooltip (str): custom tooltip for the property widget.
            tab (str): widget tab name.
        """
        widget_type = widget_type or NodePropWidgetEnum.HIDDEN.value
        tab = tab or "Properties"

        if name in self.properties:
            raise NodePropertyError(f"'{name}' reserved for default property.")
        if name in self._custom_prop.keys():
            raise NodePropertyError(f"'{name}' property already exists.")

        self._custom_prop[name] = value

        if self._graph_model is None:
            self._TEMP_property_widget_types[name] = widget_type
            self._TEMP_property_attrs[name] = {"tab": tab}
            if items:
                self._TEMP_property_attrs[name]["items"] = items
            if range:
                self._TEMP_property_attrs[name]["range"] = range
            if widget_tooltip:
                self._TEMP_property_attrs[name]["tooltip"] = widget_tooltip

        else:
            attrs = {self.dtype: {name: {"widget_type": widget_type, "tab": tab}}}
            if items:
                attrs[self.dtype][name]["items"] = items
            if range:
                attrs[self.dtype][name]["range"] = range
            if widget_tooltip:
                attrs[self.dtype][name]["tooltip"] = widget_tooltip
            self._graph_model.set_node_common_properties(attrs)

    def set_property(self, name, value):
        """
        Args:
            name (str): property name.
            value (object): property value.
        """
        if name in self.properties:
            self.properties[name] = value
        elif name in self._custom_prop.keys():
            self._custom_prop[name] = value
        else:
            raise NodePropertyError(f"No property '{name}'")

    def get_property(self, name):
        """
        Args:
            name (str): property name.

        Returns:
            object: property value.
        """
        if name in self.properties:
            return self.properties[name]
        return self._custom_prop.get(name)

    def is_custom_property(self, name):
        """
        Args:
            name (str): property name.

        Returns:
            bool: true if custom property.
        """
        return name in self._custom_prop

    def get_widget_type(self, name):
        """
        Args:
            name (str): property name.

        Returns:
            int: node property widget type.
        """
        model = self._graph_model

        if model is None:
            return self._TEMP_property_widget_types.get(name)
        return model.get_node_common_properties(self.dtype)[name]["widget_type"]

    def get_tab_name(self, name):
        """
        Args:
            name (str): property name.

        Returns:
            str: name of the tab for the properties bin.
        """
        model = self._graph_model
        if model is None:
            attrs = self._TEMP_property_attrs.get(name)
            if attrs:
                return attrs[name].get("tab")
            return
        return model.get_node_common_properties(self.dtype)[name]["tab"]

    def add_port_accept_connection_type(
        self, port_name, port_type, node_type, accept_pname, accept_ptype, accept_ntype
    ):
        """
        Convenience function for adding to the "accept_connection_types" dict.
        If the node graph model is unavailable yet then we store it to a
        temp var that gets deleted.

        Args:
            port_name (str): current port name.
            port_type (str): current port type.
            node_type (str): current port node type.
            accept_pname (str):port name to accept.
            accept_ptype (str): port type accept.
            accept_ntype (str):port node type to accept.
        """
        model = self._graph_model
        if model:
            model.add_port_accept_connection_type(
                port_name,
                port_type,
                node_type,
                accept_pname,
                accept_ptype,
                accept_ntype,
            )
            return

        connection_data = self._TEMP_accept_connection_types
        keys = [node_type, port_type, port_name, accept_ntype]
        for key in keys:
            if key not in connection_data.keys():
                connection_data[key] = {}
            connection_data = connection_data[key]

        if accept_ptype not in connection_data:
            connection_data[accept_ptype] = set([accept_pname])
        else:
            connection_data[accept_ptype].add(accept_pname)

    def add_port_reject_connection_type(
        self, port_name, port_type, node_type, reject_pname, reject_ptype, reject_ntype
    ):
        """
        Convenience function for adding to the "reject_connection_types" dict.
        If the node graph model is unavailable yet then we store it to a
        temp var that gets deleted.

        Args:
            port_name (str): current port name.
            port_type (str): current port type.
            node_type (str): current port node type.
            reject_pname:
            reject_ptype:
            reject_ntype:

        Returns:

        """
        model = self._graph_model
        if model:
            model.add_port_reject_connection_type(
                port_name,
                port_type,
                node_type,
                reject_pname,
                reject_ptype,
                reject_ntype,
            )
            return

        connection_data = self._TEMP_reject_connection_types
        keys = [node_type, port_type, port_name, reject_ntype]
        for key in keys:
            if key not in connection_data.keys():
                connection_data[key] = {}
            connection_data = connection_data[key]

        if reject_ptype not in connection_data:
            connection_data[reject_ptype] = set([reject_pname])
        else:
            connection_data[reject_ptype].add(reject_pname)

    @property
    def properties(self):
        """
        return all default node properties.

        Returns:
            dict: default node properties.
        """
        props = self.to_dict[self.id].copy()
        props["id"] = self.id
        return props

    @property
    def custom_properties(self):
        """
        return all custom properties specified by the user.

        Returns:
            dict: user defined properties.
        """
        return self._custom_prop

    @property
    def to_dict(self):
        node_dict = self.model_dump(exclude={"inputs", "outputs", "id"})

        # NOTE: port_dict: Dict[str, PortModel]
        def _get_connected_ports(port_dict):
            return {name: model.connected_ports for name, model in port_dict.items()}

        # NOTE: port_dict: Dict[str, PortModel]
        def _get_ports(port_dict):
            return [
                {
                    "name": name,
                    "multi_connection": model.multi_connection,
                    "display_name": model.display_name,
                }
                for name, model in port_dict.items()
                if self.port_deletion_allowed
            ]

        node_dict["inputs"] = _get_connected_ports(self.inputs)
        node_dict["outputs"] = _get_connected_ports(self.inputs)
        node_dict["input_ports"] = _get_ports(self.inputs)
        node_dict["output_ports"] = _get_ports(self.outputs)
        node_dict["custom"] = self._custom_prop

        return {self.id: node_dict}

    # TODO: Deprecated for simplefy
    # @property
    # def serial(self):
    #     """
    #     Serialize model information to a string.

    #     Returns:
    #         str: serialized JSON string.
    #     """
    #     return json.dumps(self.to_dict)


class NodeObject(object):
    """
    The ``NodeGraphQt.NodeObject`` class is the main base class that all
    nodes inherit from.

    .. inheritance-diagram:: NodeGraphQt.NodeObject

    Args:
        qgraphics_item (AbstractNodeItem): QGraphicsItem item used for drawing.
    """

    __identifier__ = "nodeGraphQt.nodes"
    """
    Unique node identifier domain. eg. ``"io.github.jchanvfx"``

    .. important:: re-implement this attribute to provide a unique node type.
    
        .. code-block:: python
            :linenos:
    
            from NodeGraphQt import NodeObject
    
            class ExampleNode(NodeObject):
    
                # unique node identifier domain.
                __identifier__ = 'io.github.jchanvfx'
    
                def __init__(self):
                    ...
    
    :return: node type domain.
    :rtype: str
    
    :meta hide-value:
    """

    NODE_NAME = None
    """
    Initial base node name.

    .. important:: re-implement this attribute to provide a base node name.
    
        .. code-block:: python
            :linenos:
    
            from NodeGraphQt import NodeObject
    
            class ExampleNode(NodeObject):
    
                # initial default node name.
                NODE_NAME = 'Example Node'
    
                def __init__(self):
                    ...
    
    :return: node name
    :rtype: str
    
    :meta hide-value:
    """

    def __init__(self):
        self._graph = None

        self._model = NodeModel()
        self._model.dtype = self.dtype()
        self._model.name = self.NODE_NAME

        self._view = NodeItem()
        self._view.dtype = self.dtype()
        self._view.name = self.model.name
        self._view.id = self._model.id
        self._view.layout_direction = self._model.layout_direction

    def __repr__(self):
        msg = f"{self.__class__.__name__}('{self.NODE_NAME}')"
        msg = f"<{msg} object at {hex(id(self))}>"
        return msg

    @classmethod
    def dtype(cls):
        """
        Node type identifier followed by the class name.
        `eg.` ``"nodeGraphQt.nodes.NodeObject"``

        Returns:
            str: node type (``__identifier__.__className__``)
        """
        # TODO: why use @classmethod for NodeObject dtype
        # NodeGraphQt.errors.NodeRegistrationError: node type
        # `<property object at 0x000001CA6D70B7E0>` already registered
        # to `<class 'NodeGraphQt.nodes.backdrop_node.BackdropNode'>`!
        # Please specify a new plugin class name or __identifier__.
        return cls.__identifier__ + "." + cls.__name__

    @property
    def id(self):
        """
        The node unique id.

        Returns:
            str: unique identifier string to the node.
        """
        return self.model.id

    @property
    def graph(self):
        """
        The parent node graph.

        Returns:
            NodeGraphQt.NodeGraph: node graph instance.
        """
        return self._graph

    @property
    def view(self):
        """
        Returns the :class:`QtWidgets.QGraphicsItem` used in the scene.

        Returns:
            NodeGraphQt.qgraphics.node_abstract.AbstractNodeItem: node item.
        """
        return self._view

    @property
    def model(self):
        """
        Return the node model.

        Returns:
            NodeGraphQt.base.model.NodeModel: node model object.
        """
        return self._model

    def update(self):
        """
        Update the node view from model.
        """
        settings = self.model.to_dict[self.model.id]
        settings["id"] = self.model.id
        self.view.from_dict(settings)

    # TODO: Deprecated for simplefy
    # def create_property(
    #     self,
    #     name,
    #     value,
    #     items=None,
    #     range=None,
    #     widget_type=None,
    #     widget_tooltip=None,
    #     tab=None,
    # ):
    #     """
    #     Creates a custom property to the node.

    #     See Also:
    #         Custom node properties bin widget
    #         :class:`NodeGraphQt.PropertiesBinWidget`

    #     Hint:
    #         To see all the available property widget types to display in
    #         the ``PropertiesBinWidget`` widget checkout
    #         :attr:`NodeGraphQt.constants.NodePropWidgetEnum`.

    #     Args:
    #         name (str): name of the property.
    #         value (object): data.
    #         items (list[str]): items used by widget type
    #             attr:`NodeGraphQt.constants.NodePropWidgetEnum.QCOMBO_BOX`
    #         range (tuple or list): ``(min, max)`` values used by
    #             :attr:`NodeGraphQt.constants.NodePropWidgetEnum.SLIDER`
    #         widget_type (int): widget flag to display in the
    #             :class:`NodeGraphQt.PropertiesBinWidget`
    #         widget_tooltip (str): widget tooltip for the property widget
    #             displayed in the :class:`NodeGraphQt.PropertiesBinWidget`
    #         tab (str): name of the widget tab to display in the
    #             :class:`NodeGraphQt.PropertiesBinWidget`.
    #     """
    #     widget_type = widget_type or NodePropWidgetEnum.HIDDEN.value
    #     self.model.add_property(
    #         name, value, items, range, widget_type, widget_tooltip, tab
    #     )

    # TODO: Deprecated for simplefy
    # def get_property(self, name):
    #     """
    #     Return the node custom property.

    #     Args:
    #         name (str): name of the property.

    #     Returns:
    #         object: property data.
    #     """
    #     if self.graph and name == "selected":
    #         self.model.set_property(name, self.view.selected)

    #     return self.model.get_property(name)

    # TODO: Deprecated for simplefy
    # def set_property(self, name, value, push_undo=True):
    #     """
    #     Set the value on the node custom property.

    #     Note:
    #         When setting the node ``"name"`` property a new unique name will be
    #         used if another node in the graph has the same node name.

    #     Args:
    #         name (str): name of the property.
    #         value (object): property data (python built in types).
    #         push_undo (bool): register the command to the undo stack. (default: True)
    #     """
    #     # prevent signals from causing an infinite loop.
    #     if self.model.get_property(name) is value:
    #         return

    #     print("checkpoint 1")
    #     # prevent nodes from have the same name.
    #     if self.graph and name == "name":
    #         value = self.graph.get_unique_name(value)
    #         self.NODE_NAME = value

    #     if self.graph:
    #         print("checkpoint 3")
    #         undo_cmd = PropertyChangedCmd(self, name, value)
    #         if name == "name":
    #             # TODO: self.name() -> self.view.name
    #             undo_cmd.setText(f"renamed '{self.view.name}' to '{value}'")
    #         if push_undo:
    #             undo_stack = self.graph.undo_stack()
    #             undo_stack.push(undo_cmd)
    #         else:
    #             undo_cmd.redo()
    #     else:
    #         print("checkpoint 4")
    #         if hasattr(self.view, name):
    #             setattr(self.view, name, value)
    #         self.model.set_property(name, value)

    #     print("checkpoint 5")
    #     # redraw the node for custom properties.
    #     if self.model.is_custom_property(name):
    #         self.view.draw_node()

    # TODO: Deprecated for simplefy
    # def properties(self):
    #     """
    #     Returns all the node properties.

    #     Returns:
    #         dict: a dictionary of node properties.
    #     """
    #     props = self.model.to_dict[self.id].copy()
    #     props["id"] = self.id
    #     return props

    # TODO: Deprecated for simplefy
    # def has_property(self, name):
    #     """
    #     Check if node custom property exists.

    #     Args:
    #         name (str): name of the node.

    #     Returns:
    #         bool: true if property name exists in the Node.
    #     """
    #     return name in self.model.custom_properties.keys()

    # TODO: Deprecated for simplefy
    # def set_view(self, item):
    #     """
    #     Set a new ``QGraphicsItem`` item to be used as the view.
    #     (the provided qgraphics item must be subclassed from the
    #     ``AbstractNodeItem`` object.)

    #     Args:
    #         item (NodeGraphQt.qgraphics.node_abstract.AbstractNodeItem): node item.
    #     """
    #     if self._view:
    #         old_view = self._view
    #         scene = self._view.scene()
    #         scene.removeItem(old_view)
    #         self._view = item
    #         scene.addItem(self._view)
    #     else:
    #         self._view = item
    #     self.NODE_NAME = self._view.name

    #     # update the view.
    #     self.update()

    # TODO: Deprecated for simplefy
    # def set_model(self, model):
    #     """
    #     Set a new model to the node model.
    #     (Setting a new node model will also update the views qgraphics item.)

    #     Args:
    #         model (NodeGraphQt.base.model.NodeModel): node model object.
    #     """
    #     self._model = model
    #     self._model.dtype = self.dtype()
    #     self._model.id = self.view.id

    #     # update the view.
    #     self.update()

    # TODO: Deprecated for simplefy
    # def update_model(self):
    #     """
    #     Update the node model from view.
    #     """
    #     print("update_model 2")
    #     for name, val in self.view.properties.items():
    #         if name in self.model.properties.keys():
    #             setattr(self.model, name, val)
    #         if name in self.model.custom_properties.keys():
    #             self.model.custom_properties[name] = val

    # TODO: Deprecated for simplefy
    # def serialize(self):
    #     """
    #     Serialize node model to a dictionary.

    #     example:

    #     .. highlight:: python
    #     .. code-block:: python

    #         {'0x106cf75a8': {
    #             'name': 'foo node',
    #             'color': (48, 58, 69, 255),
    #             'border_color': (85, 100, 100, 255),
    #             'text_color': (255, 255, 255, 180),
    #             'type': 'io.github.jchanvfx.MyNode',
    #             'selected': False,
    #             'disabled': False,
    #             'visible': True,
    #             'inputs': {
    #                 <port_name>: {<node_id>: [<port_name>, <port_name>]}
    #             },
    #             'outputs': {
    #                 <port_name>: {<node_id>: [<port_name>, <port_name>]}
    #             },
    #             'input_ports': [<port_name>, <port_name>],
    #             'output_ports': [<port_name>, <port_name>],
    #             'width': 0.0,
    #             'height: 0.0,
    #             'pos': (0.0, 0.0),
    #             'layout_direction': 0,
    #             'custom': {},
    #             }
    #         }

    #     Returns:
    #         dict: serialized node
    #     """
    #     return self.model.to_dict

    # TODO: Deprecated for simplefy
    # def name(self):
    #     """
    #     Name of the node.

    #     Returns:
    #         str: name of the node.
    #     """
    #     return self.model.name

    # TODO: Deprecated for simplefy
    # def set_name(self, name=""):
    #     """
    #     Set the name of the node.

    #     Args:
    #         name (str): name for the node.
    #     """
    #     self.set_property("name", name)

    # TODO: Deprecated for simplefy
    # def disabled(self):
    #     """
    #     Returns whether the node is enabled or disabled.

    #     Returns:
    #         bool: True if the node is disabled.
    #     """
    #     return self.model.disabled

    # TODO: Deprecated for simplefy
    # def set_disabled(self, mode=False):
    #     """
    #     Set the node state to either disabled or enabled.

    #     Args:
    #         mode(bool): True to disable node.
    #     """
    #     self.set_property("disabled", mode)

    # TODO: Deprecated for simplefy
    # def selected(self):
    #     """
    #     Returns the selected state of the node.

    #     Returns:
    #         bool: True if the node is selected.
    #     """
    #     self.model.selected = self.view.isSelected()
    #     return self.model.selected

    # TODO: Deprecated for simplefy
    # def set_selected(self, selected=True):
    #     """
    #     Set the node to be selected or not selected.

    #     Args:
    #         selected (bool): True to select the node.
    #     """
    #     self.set_property("selected", selected)

    # TODO: Deprecated for simplefy
    # def set_x_pos(self, x):
    #     """
    #     Set the node horizontal X position in the node graph.

    #     Args:
    #         x (float or int): node X position.
    #     """
    #     y = self.pos()[1]
    #     self.set_pos(float(x), y)

    # TODO: Deprecated for simplefy
    # def set_y_pos(self, y):
    #     """
    #     Set the node horizontal Y position in the node graph.

    #     Args:
    #         y (float or int): node Y position.
    #     """

    #     x = self.pos()[0]
    #     self.set_pos(x, float(y))

    # TODO: Deprecated for simplefy
    # def set_pos(self, x, y):
    #     """
    #     Set the node X and Y position in the node graph.

    #     Args:
    #         x (float or int): node X position.
    #         y (float or int): node Y position.
    #     """
    #     self.set_property("pos", [float(x), float(y)])

    # TODO: Deprecated for simplefy
    # def x_pos(self):
    #     """
    #     Get the node X position in the node graph.

    #     Returns:
    #         float: x position.
    #     """
    #     return self.model.pos[0]

    # TODO: Deprecated for simplefy
    # def y_pos(self):
    #     """
    #     Get the node Y position in the node graph.

    #     Returns:
    #         float: y position.
    #     """
    #     return self.model.pos[1]

    # TODO: Deprecated for simplefy
    # def pos(self):
    #     """
    #     Get the node XY position in the node graph.

    #     Returns:
    #         list[float, float]: x, y position.
    #     """
    #     if self.view.xy_pos and self.view.xy_pos != self.model.pos:
    #         self.model.pos = self.view.xy_pos

    #     return self.model.pos

    # TODO: Deprecated for simplefy
    # def layout_direction(self):
    #     """
    #     Returns layout direction for this node.

    #     See Also:
    #         :meth:`NodeObject.set_layout_direction`

    #     Returns:
    #         int: node layout direction.
    #     """
    #     return self.model.layout_direction

    # TODO: Deprecated for simplefy
    # def set_layout_direction(self, value=0):
    #     """
    #     Sets the node layout direction to either horizontal or vertical on
    #     the current node only.

    #     `Implemented in` ``v0.3.0``

    #     See Also:
    #         :meth:`NodeGraph.set_layout_direction`
    #         :meth:`NodeObject.layout_direction`

    #     Warnings:
    #         This function does not register to the undo stack.

    #     Args:
    #         value (int): layout direction mode.
    #     """
    #     self.model.layout_direction = value
    #     self.view.layout_direction = value
