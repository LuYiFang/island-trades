import os.path
import pickle
import sys
import tkinter as tk
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit,
                             QComboBox, QCheckBox, QVBoxLayout)


from Island import ExchangeGraph, Stock, Exchange, IslandGraph
from UI import MainWindow

if __name__ == '__main__':
    island_graph = IslandGraph.read()
    if island_graph is None:
        island_graph = IslandGraph()

    stock = Stock.read()
    if stock is None:
        stock = Stock()

    app = QApplication(sys.argv)
    window = MainWindow(island_graph, stock)
    window.show()
    sys.exit(app.exec_())
