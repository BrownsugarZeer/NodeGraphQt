from NodeGraphQt.constants import (
    LayoutDirectionEnum,
    PipeLayoutEnum,
)
from NodeGraphQt.errors import PortError


class NodeGraphModel:
    """
    Data dump for a node graph.
    """

    def __init__(self):
        self.__common_node_props = {}

        self.accept_connection_types = {}
        self.reject_connection_types = {}

        self.nodes = {}
        self.session = ""
        self.acyclic = True
        self.pipe_collision = False
        self.pipe_slicing = True
        self.pipe_style = PipeLayoutEnum.CURVED.value
        self.layout_direction = LayoutDirectionEnum.HORIZONTAL.value

    @property
    def common_properties(self):
        """
        Return all common node properties.

        Returns:
            dict: common node properties.
                eg.
                    {'nodeGraphQt.nodes.FooNode': {
                        'my_property': {
                            'widget_type': 0,
                            'tab': 'Properties',
                            'items': ['foo', 'bar', 'test'],
                            'range': (0, 100)
                            }
                        }
                    }
        """
        return self.__common_node_props

    def set_node_common_properties(self, attrs: dict):
        """
        Store common node properties.

        Args:
            attrs (dict): common node properties.
                eg.
                    {'nodeGraphQt.nodes.FooNode': {
                        'my_property': {
                            'widget_type': 0,
                            'tab': 'Properties',
                            'items': ['foo', 'bar', 'test'],
                            'range': (0, 100)
                            }
                        }
                    }
        """
        for node_type in attrs.keys():
            node_props = attrs[node_type]

            if node_type not in self.__common_node_props:
                self.__common_node_props[node_type] = node_props
                continue

            for prop_name, prop_attrs in node_props.items():
                common_props = self.__common_node_props[node_type]
                if prop_name not in common_props.keys():
                    common_props[prop_name] = prop_attrs
                    continue
                common_props[prop_name].update(prop_attrs)

    def get_node_common_properties(self, node_type):
        """
        Return all the common properties for a registered node.

        Args:
            node_type (str): node type.

        Returns:
            dict: node common properties.
        """
        return self.__common_node_props.get(node_type)

    def add_accept_port_type(
        self, node, port, accept_pname, accept_ptype, accept_ntype
    ):
        """
        Add an accept constrain to a specified node port.

        Once a constraint has been added only ports of that type specified will
        be allowed a pipe connection.

        Args:
            node (NodeGraphQt.BaseNode): node to assign constrain to.
            port (NodeGraphQt.Port): port to assign constrain to.
            accept_pname (str):port name to accept.
            accept_ptype (str): port type accept.
            accept_ntype (str):port node type to accept.
        """
        port_name = port.name
        port_type = port.dtype
        node_type = node.dtype()

        node_ports = node._inputs + node._outputs
        if port not in node_ports:
            raise PortError(f"Node does not contain port: '{port}'")

        connection_data = self.accept_connection_types
        keys = [node_type, port_type, port_name, accept_ntype]
        for key in keys:
            if key not in connection_data:
                connection_data[key] = {}
            connection_data = connection_data[key]

        if accept_ptype not in connection_data:
            connection_data[accept_ptype] = set([accept_pname])
        else:
            # ensure data remains a set instead of list after json de-serialize
            connection_data[accept_ptype] = set(connection_data[accept_ptype]) | {
                accept_pname
            }

    def add_reject_port_type(
        self, node, port, reject_pname, reject_ptype, reject_ntype
    ):
        """
        Convenience function for adding to the "reject_connection_types" dict.

        Args:
            node (NodeGraphQt.BaseNode): node to assign constrain to.
            port (NodeGraphQt.Port): port to assign constrain to.
            reject_pname (str): port name to reject.
            reject_ptype (str): port type to reject.
            reject_ntype (str): port node type to reject.
        """
        port_name = port.name
        port_type = port.dtype
        node_type = node.dtype()

        node_ports = node._inputs + node._outputs
        if port not in node_ports:
            raise PortError(f"Node does not contain port: '{port}'")

        connection_data = self.reject_connection_types
        keys = [node_type, port_type, port_name, reject_ntype]
        for key in keys:
            if key not in connection_data:
                connection_data[key] = {}
            connection_data = connection_data[key]

        if reject_ptype not in connection_data:
            connection_data[reject_ptype] = set([reject_pname])
        else:
            # ensure data remains a set instead of list after json de-serialize
            connection_data[reject_ptype] = set(connection_data[reject_ptype]) | {
                reject_pname
            }
