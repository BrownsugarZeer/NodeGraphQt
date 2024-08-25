from NodeGraphQt.nodes.base_model import NodeObject


class NodeFactory:
    """
    Node factory that stores all the node types.
    """

    def __init__(self):
        self.__names = {}
        self.__nodes = {}

    @property
    def names(self):
        """
        Return all currently registered node type identifiers.

        Returns:
            dict: key=<node name, value=node_type
        """
        return self.__names

    @property
    def nodes(self):
        """
        Return all registered nodes.

        Returns:
            dict: key=node identifier, value=node class
        """
        return self.__nodes

    def create_node_instance(self, node_type=None):
        """
        create node object by the node type identifier or alias.

        Args:
            node_type (str): node type or optional alias name.

        Returns:
            NodeGraphQt.NodeObject: new node object.
        """
        _NodeClass = self.__nodes.get(node_type)
        if _NodeClass:
            return _NodeClass()

    def register_node(
        self,
        node: NodeObject,
        name: str,
        node_type: str,
    ):
        """
        register the node.

        Args:
            node (NodeGraphQt.NodeObject): node object.
            alias (str): custom alias for the node identifier (optional).
        """
        if self.__nodes.get(node_type):
            print(
                f"node type `{node_type}` already registered to `{self.__nodes[node_type]}`! "
                "Please specify a new plugin class name or __identifier__."
            )
            return

        self.__nodes[node_type] = node

        if self.__names.get(name):
            self.__names[name].append(node_type)
        else:
            self.__names[name] = [node_type]

    def clear_registered_nodes(self):
        """
        clear out registered nodes, to prevent conflicts on reset.
        """
        self.__nodes.clear()
        self.__names.clear()
