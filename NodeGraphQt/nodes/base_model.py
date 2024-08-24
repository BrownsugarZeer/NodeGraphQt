from typing import List, Dict, Tuple, Optional
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict

from NodeGraphQt.constants import (
    LayoutDirectionEnum,
    NodePropWidgetEnum,
)
from NodeGraphQt.errors import NodePropertyError
from NodeGraphQt.nodes.base_item import NodeItem
from NodeGraphQt.base.model import NodeGraphModel


class NodeModel(BaseModel):
    """
    Data dump for a node object.
    """

    # TODO: rename all dtype to `identifier`
    dtype: str
    name: str
    id: str = Field(default_factory=lambda: uuid4().hex)
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
    _property_attrs: Dict = {}

    # temp store the property widget types.
    # (deleted when node is added to the graph)
    _property_widget_types: Dict = {
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
        if name in self._custom_prop:
            raise NodePropertyError(f"'{name}' property already exists.")

        self._custom_prop[name] = value

        if self._graph_model is None:
            self._property_widget_types[name] = widget_type
            self._property_attrs[name] = {"tab": tab}
            if items:
                self._property_attrs[name]["items"] = items
            if range:
                self._property_attrs[name]["range"] = range
            if widget_tooltip:
                self._property_attrs[name]["tooltip"] = widget_tooltip

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
        elif name in self._custom_prop:
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
            return self._property_widget_types.get(name)
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
            attrs = self._property_attrs.get(name)
            if attrs:
                return attrs[name].get("tab")
            return
        return model.get_node_common_properties(self.dtype)[name]["tab"]

    @property
    def properties(self):
        """
        return all default node properties.

        Returns:
            dict: default node properties.
        """
        node_dict = self.model_dump(exclude={"inputs", "outputs"})

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

        return node_dict

    @property
    def custom_properties(self):
        """
        return all custom properties specified by the user.

        Returns:
            dict: user defined properties.
        """
        return self._custom_prop


class NodeObject:
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

    def __init__(self, qgraphics_views=None):
        self._graph = None

        self._model = NodeModel(dtype=self.dtype(), name=self.NODE_NAME)

        self._view = qgraphics_views or NodeItem()
        self._view.dtype = self.model.dtype
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
        self.view.from_dict(self.model.properties)
