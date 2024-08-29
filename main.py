import os.path
import pickle
import sys
import tkinter as tk
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit,
                             QComboBox, QCheckBox, QVBoxLayout)


from Island import ExchangeGraph, Stock, Exchange, IslandGraph
from UI import MainWindow

if __name__ == '__main__':
    stock = Stock({
        '蓮花': 3,
        '豌豆': 5,
        '櫻花': 2,
    })

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

    # print('pass islands')
    # print(island_graph.find_pass_islands('B', 'J'))

    exchange_graph = ExchangeGraph('A', 11500, stock, island_graph)
    exchange_graph.add_trade({
        'A': ('蓮花', '海參', 3),
        'B': ('海參', '茶杯', 3),
        'C': ('茶杯', '靈丹', 2),
        'D': ('靈丹', '密藥', 1),
        'E': ('櫻花', '觸鬚', 3),
        'F': ('觸鬚', '沙漏', 3),
        'G': ('沙漏', '海賊刀', 2),
        'H': ('海賊刀', '眼淚', 1),
        'I': ('豌豆', '石板', 3),
        'J': ('石板', '血液', 3),
        'K': ('血液', '騎士槍', 2),
        'L': ('騎士槍', '幼蟲', 1),
        'M': ('麵糰', '蓮花', 1),
        'N': ('羽毛', '櫻花', 1),
        'O': ('皮革', '豌豆', 1),
    })

    # exchange_graph.schedule_routes()

    # root = tk.Tk()
    # app = UI(root)
    # root.mainloop()

    app = QApplication(sys.argv)
    window = MainWindow(island_graph)
    window.show()
    sys.exit(app.exec_())
