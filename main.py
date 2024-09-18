import sys
from PyQt5.QtWidgets import QApplication

from Island import IslandGraph
from Stock import Stock
from UI.UI import MainWindow


if __name__ == '__main__':
    island_graph = IslandGraph('伊利亞')
    stock = Stock()

    app = QApplication(sys.argv)
    window = MainWindow(island_graph, stock)
    window.show()
    sys.exit(app.exec_())
