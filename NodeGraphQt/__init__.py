"""
**NodeGraphQt** is a node graph framework that can be implemented and re purposed
into applications that supports **PySide2**.

project: https://github.com/jchanvfx/NodeGraphQt
documentation: https://jchanvfx.github.io/NodeGraphQt/api/html/index.html

example code:

.. code-block:: python
    :linenos:

    from NodeGraphQt import QtWidgets, NodeGraph, BaseNode


    class MyNode(BaseNode):

        __identifier__ = 'io.github.jchanvfx'
        NODE_NAME = 'My Node'

        def __init__(self):
            super().__init__()
            self.add_input('foo', color=(180, 80, 0))
            self.add_output('bar')

    if __name__ == '__main__':
        app = QtWidgets.QApplication([])
        graph = NodeGraph()

        graph.register_node(BaseNode)

        node_a = graph.create_node('io.github.jchanvfx.MyNode', name='Node A')
        node_b = graph.create_node('io.github.jchanvfx.MyNode', name='Node B', color='#5b162f')

        node_a.set_input(0, node_b.output(0))

        viewer = graph.viewer()
        viewer.show()

        app.exec_()
"""

from .pkg_info import __version__ as VERSION
from .pkg_info import __license__ as LICENSE

from NodeGraphQt import base  # noqa
from NodeGraphQt import nodes  # noqa
from NodeGraphQt import qgraphics  # noqa
from NodeGraphQt import widgets  # noqa


from icecream import install

install()

__version__ = VERSION
