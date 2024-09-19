import logging
import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

from Island import IslandGraph
from Stock import Stock
from UI.UI import MainWindow
from utility import resource_path

# for debug
# logging.basicConfig(filename='app.log', level=logging.DEBUG)


if __name__ == '__main__':
    island_graph = IslandGraph('伊利亞')
    stock = Stock()

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path('static/icon.ico')))
    window = MainWindow(island_graph, stock)
    window.show()
    sys.exit(app.exec_())
