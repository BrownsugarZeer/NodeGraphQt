from PySide6 import QtWidgets, QtGui

from NodeGraphQt.constants import NodeEnum, ViewerEnum, ViewerNavEnum


class NodeGraphWidget(QtWidgets.QTabWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.setTabBarAutoHide(True)
        dark_viewer_color = (
            QtGui.QColor(*ViewerEnum.BACKGROUND_COLOR.value).darker(120).getRgb()
        )
        text_color = tuple(map(lambda i, j: i - j, (255, 255, 255), dark_viewer_color))

        text_color = ",".join(map(str, text_color))
        dark_viewer_color = ",".join(map(str, dark_viewer_color[:-1]))
        viewer_color = ",".join(map(str, ViewerEnum.BACKGROUND_COLOR.value))
        viewer_nav_color = ",".join(map(str, ViewerNavEnum.BACKGROUND_COLOR.value))
        selected_color = ",".join(map(str, NodeEnum.SELECTED_BORDER_COLOR.value))
        _stylesheet = f"""\
        QWidget {{
            background-color: rgb({viewer_color});
        }}
        QTabWidget::pane {{
            background: rgb({viewer_color});
            border: 0px;
            border-top: 0px solid rgb({dark_viewer_color});
        }}
        QTabBar::tab {{
            background: rgb({dark_viewer_color});
            border: 0px solid black;
            color: rgba({text_color},30);
            min-width: 10px;
            padding: 10px 20px;
        }}
        QTabBar::tab:selected {{
            color: rgb({text_color});
            background: rgb({viewer_nav_color});
            border-top: 1px solid rgb({selected_color});
        }}
        QTabBar::tab:hover {{
            color: rgb({text_color});
            border-top: 1px solid rgb({selected_color});
        }}"""
        self.setStyleSheet(_stylesheet)

    def add_viewer(self, viewer, name, node_id):
        self.addTab(viewer, name)
        index = self.indexOf(viewer)
        self.setTabToolTip(index, node_id)
        self.setCurrentIndex(index)

    def remove_viewer(self, viewer):
        index = self.indexOf(viewer)
        self.removeTab(index)
