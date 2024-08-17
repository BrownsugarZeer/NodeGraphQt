from PySide6 import QtGui, QtCore, QtWidgets

from NodeGraphQt.constants import ViewerEnum


class BaseMenu(QtWidgets.QMenu):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        text_color = tuple(
            map(lambda i, j: i - j, (255, 255, 255), ViewerEnum.BACKGROUND_COLOR.value)
        )
        selected_color = self.palette().highlight().color().getRgb()

        text_color = ",".join(map(str, text_color))
        selected_color = ",".join(map(str, selected_color[:-1]))
        background_color = ",".join(map(str, ViewerEnum.BACKGROUND_COLOR.value))
        stylesheet = f"""\
        QMenu {{
            color:rgb({text_color});
            background-color:rgb({background_color});
            border:1px solid rgba({text_color},30);
            border-radius:3px;
        }}
        QMenu::item {{
            padding:5px 18px 2px;
            background-color:transparent;
        }}
        QMenu::item:selected {{
            color:rgb({text_color});
            background-color:rgba({selected_color},200);
        }}
        QMenu::item:disabled {{
            color:rgba({text_color},60);
            background-color:rgba({background_color},200);
        }}
        QMenu::separator {{
            height:1px;
            background:rgba({text_color},50);
            margin:4px 8px;
        }}"""
        self.setStyleSheet(stylesheet)
        self.node_class = None
        self.graph = None

    def get_menu(self, name, node_id=None):
        for action in self.actions():
            menu = action.menu()
            if not menu:
                continue
            if menu.title() == name:
                return menu
            if node_id and menu.node_class:
                node = menu.graph.get_node_by_id(node_id)
                if isinstance(node, menu.node_class):
                    return menu

    def get_menus(self, node_class):
        menus = []
        for action in self.actions():
            menu = action.menu()
            if menu.node_class:
                if issubclass(menu.node_class, node_class):
                    menus.append(menu)
        return menus


class GraphAction(QtGui.QAction):

    executed = QtCore.Signal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph = None
        self.triggered.connect(self._on_triggered)

    def _on_triggered(self):
        self.executed.emit(self.graph)

    def get_action(self, name):
        for action in self.qmenu.actions():
            if not action.menu() and action.text() == name:
                return action


class NodeAction(GraphAction):

    executed = QtCore.Signal(object, object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node_id = None

    def _on_triggered(self):
        node = self.graph.get_node_by_id(self.node_id)
        self.executed.emit(self.graph, node)
