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
        island_graph.add_edge('A', 'K', 1)
        island_graph.add_edge('A', 'L', 1)
        island_graph.add_edge('A', 'B', 1)
        island_graph.add_edge('B', 'C', 1)
        island_graph.add_edge('B', 'D', 1)
        island_graph.add_edge('C', 'D', 1)
        island_graph.add_edge('D', 'E', 1)
        island_graph.add_edge('D', 'F', 1)
        island_graph.add_edge('E', 'F', 1)
        island_graph.add_edge('E', 'G', 2)
        island_graph.add_edge('E', 'H', 1)
        island_graph.add_edge('F', 'G', 1)
        island_graph.add_edge('F', 'H', 2)
        island_graph.add_edge('G', 'H', 1)
        island_graph.add_edge('G', 'I', 1)
        island_graph.add_edge('G', 'J', 2)
        island_graph.add_edge('H', 'I', 2)
        island_graph.add_edge('H', 'J', 1)
        island_graph.add_edge('I', 'J', 1)
        island_graph.add_edge('M', 'B', 1)
        island_graph.add_edge('M', 'D', 1)
        island_graph.add_edge('M', 'A', 2)
        island_graph.add_edge('N', 'F', 2)
        island_graph.add_edge('N', 'I', 2)
        island_graph.add_edge('O', 'J', 1)

        island_graph.cluster_islands(4)

    app = QApplication(sys.argv)
    window = MainWindow(island_graph)
    window.show()
    sys.exit(app.exec_())
