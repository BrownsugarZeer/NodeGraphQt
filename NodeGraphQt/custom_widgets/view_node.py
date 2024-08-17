from NodeGraphQt import BaseNode


class DataViewerNode(BaseNode):
    __identifier__ = "task_manager.view"
    NODE_NAME = "Result Viewer"

    def __init__(self):
        super().__init__()
        self.in_port = self.add_input("data")
        self.add_text_input("data", "Shape", tab="widgets")

    def run(self):
        for from_port in self.in_port.connected_ports():
            value = from_port.node().get_property(from_port.name())
            self.set_property("data", value)

    def on_input_connected(self, to_port, from_port):
        self.run()

    def on_input_disconnected(self, to_port, from_port):
        self.set_property("data", None)
