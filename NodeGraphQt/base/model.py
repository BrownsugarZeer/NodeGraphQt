from NodeGraphQt.constants import (
    LayoutDirectionEnum,
    PipeLayoutEnum,
)


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

    def set_node_common_properties(self, attrs):
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

            if node_type not in self.__common_node_props.keys():
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
