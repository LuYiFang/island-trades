import logging

from PyQt5 import QtCore

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
)

from Exchange import Scheduler
from UI_schedule import TopWidget, MiddleWidget, RouteViewWidget
from UI_stock import StockWidget
from UI_widget import FileChooser, Worker


class MainWindow(QWidget):
    submit_button_signal = QtCore.pyqtSignal(list)
    stock_update_signal = QtCore.pyqtSignal(list)
    income_update_signal = QtCore.pyqtSignal(int)
    upload_exchange_signal = QtCore.pyqtSignal(str)

    def __init__(self, island_graph, stock):
        super(MainWindow, self).__init__()

        self.stock = stock
        self.island_graph = island_graph
        self.islands = sorted(list(island_graph.island_group_map.keys()))
        self.exchange_graph = Scheduler(self.stock, self.island_graph)

        self.set_font()
        self.set_theme()

        main_layout = QHBoxLayout(self)

        self.top_view = TopWidget(self.stock, self.exchange_graph)
        self.submit_button = QPushButton("Submit")
        self.middle_view = MiddleWidget(self.islands, self.stock)
        self.route_view = RouteViewWidget(self.stock, self.stock_update_signal, self.income_update_signal)
        self.save_exchange_button = QPushButton("Save Exchange")
        left_layout = self.add_left_area()

        self.stock_view = StockWidget(self.stock)
        right_layout = self.add_stock_view()

        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 2)

        self.setWindowTitle("Island Trade")
        self.resize(1800, 900)

        self.submit_button.clicked.connect(self.run_schedule)
        self.save_exchange_button.clicked.connect(self.save_exchange)

        self.submit_button_signal.connect(self.route_view.update_routes)
        self.stock_update_signal.connect(self.stock_view.update_items)
        self.income_update_signal.connect(self.top_view.update_income)
        self.top_view.add_item_signal.connect(self.middle_view.update_item_options)
        self.upload_exchange_signal.connect(self.middle_view.add_item_by_file)

    def add_left_area(self):
        left_layout = QVBoxLayout(self)
        self.setLayout(left_layout)

        left_layout.addWidget(self.top_view, 1)
        left_layout.addWidget(self.middle_view, 2)

        left_layout.addWidget(self.submit_button)

        import_export_layout = QHBoxLayout()
        self.setLayout(import_export_layout)
        import_export_layout.addWidget(FileChooser(self.upload_exchange_signal))
        import_export_layout.addWidget(self.save_exchange_button)
        left_layout.addLayout(import_export_layout)

        left_layout.addWidget(self.route_view, 2)
        return left_layout

    def add_stock_view(self):
        right_layout = QVBoxLayout(self)
        right_layout.addWidget(self.stock_view)
        return right_layout

    def set_font(self):
        font = QFont("Microsoft JhengHei", 12)
        QApplication.setFont(font)

    def set_theme(self):
        self.setStyleSheet("""
                    QWidget {
                        background-color: #2b2b2b;
                        color: #a9b7c6;
                    }
                    QPushButton {
                        background-color: #4C4C4C;
                        color: #a9b7c6;
                        /*border: 1px solid #5A5A5A;*/
                    }
                    QPushButton:hover {
                        background-color: #5A5A5A;
                    }
                """)

    def save_exchange(self):
        self.exchange_graph.save('save_exchanges')

    def run_schedule(self):
        exchanges = {}
        for group in self.middle_view.item_groups:
            island = group.island_combobox.currentText()
            source = group.item_combobox_source.currentText()
            target = group.item_combobox_target.currentText()
            quantity = group.quantity_input.value()
            swap_cost = group.swap_cost_input.value()
            specified_quantity = group.specified_quantity_input.value()
            exchanges[island] = (source, target, quantity, swap_cost, specified_quantity)
        try:
            exchanges = {}
            for group in self.middle_view.item_groups:
                island = group.island_combobox.currentText()
                source = group.item_combobox_source.currentText()
                target = group.item_combobox_target.currentText()
                quantity = group.ratio_input.value()
                swap_cost = group.swap_cost_input.value()
                exchanges[island] = (source, target, quantity, swap_cost)

        self.worker = Worker(exchanges, self.exchange_graph)
        self.worker.finished.connect(self.submit_button_signal.emit)
        self.worker.start()
        self.route_view.start_loading()
            self.worker = Worker(exchanges, self.exchange_graph)
            self.worker.finished.connect(self.submit_button_signal.emit)
            self.worker.start()
            self.route_view.start_loading()
        except Exception as e:
            logging.exception(e)

    def closeEvent(self, a0):
        self.stock.save()
        a0.accept()

# 算交涉力
# 接 auto sell
# 接收入
# 檢查演算法
# 記錄歷史 exchange+island
# 看要不要加stock不足排除路線
# UI 醜死了
# 存 json
