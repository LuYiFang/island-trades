import logging
from collections import defaultdict

from PyQt5 import QtCore
from PyQt5.QtCore import Qt

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QSplitter, QFrame, QSizePolicy,
)

from Scheduler import Scheduler
from UI_schedule import TopWidget, MiddleWidget, RouteViewWidget, HintWidget
from UI_stock import StockWidget
from UI_widget import FileChooser, Worker, CollapsibleSection


class MainWindow(QWidget):
    submit_button_signal = QtCore.pyqtSignal(list)
    stock_update_signal = QtCore.pyqtSignal(list)
    income_update_signal = QtCore.pyqtSignal(int)
    upload_exchange_signal = QtCore.pyqtSignal(str)
    upload_total_swap_cost_signal = QtCore.pyqtSignal(int)

    def __init__(self, island_graph, stock):
        super(MainWindow, self).__init__()

        self.stock = stock
        self.island_graph = island_graph
        self.islands = sorted(list(island_graph.island_group_map.keys()))
        self.schedule = Scheduler(self.stock, self.island_graph)

        self.set_font()
        self.set_theme()

        main_layout = QHBoxLayout(self)

        self.section_middle = CollapsibleSection()
        self.section_route_view = CollapsibleSection(False)

        self.top_view = TopWidget(self.stock, self.schedule)
        self.clean_button = QPushButton("Clean")
        self.submit_button = QPushButton("Submit")
        self.middle_view = MiddleWidget(self.islands, self.stock, self.upload_total_swap_cost_signal)
        self.route_view = RouteViewWidget(self.stock, self.schedule, self.stock_update_signal,
                                          self.income_update_signal)
        self.save_exchange_button = QPushButton("Save Exchange")
        self.save_remain_exchange_button = QPushButton("Save Remain Exchange")
        self.hint_view = HintWidget(self.stock)
        left_layout = self.add_left_area()

        self.stock_view = StockWidget(self.stock)
        right_layout = self.add_stock_view()

        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 1)

        self.setWindowTitle("Island Trade")
        self.resize(1200, 900)

        self.clean_button.clicked.connect(self.middle_view.clean_view)
        self.submit_button.clicked.connect(self.run_schedule)
        self.save_exchange_button.clicked.connect(self.save_exchange)
        self.save_remain_exchange_button.clicked.connect(self.schedule.save_exchanges_remain)

        self.submit_button_signal.connect(self.route_view.update_routes)
        self.submit_button_signal.connect(self.hint_view.generate_hints)
        self.stock_update_signal.connect(self.stock_view.update_items)
        self.income_update_signal.connect(self.top_view.update_income)
        self.top_view.add_item_signal.connect(self.middle_view.update_item_options)
        self.upload_exchange_signal.connect(self.middle_view.add_item_by_file)
        self.upload_total_swap_cost_signal.connect(self.top_view.update_total_swap_cost)

    def add_left_area(self):
        left_layout = QVBoxLayout(self)
        self.setLayout(left_layout)

        left_layout.addWidget(self.top_view, 1)

        upload_layout = QHBoxLayout()
        upload_layout.addWidget(FileChooser('Open Exchanges File', self.upload_exchange_signal))
        upload_layout.addWidget(self.clean_button)
        left_layout.addLayout(upload_layout)

        self.section_middle.add_widget(self.middle_view)
        left_layout.addWidget(self.section_middle)

        action_layout = QHBoxLayout()
        action_layout.addWidget(self.save_exchange_button)
        action_layout.addWidget(self.save_remain_exchange_button)
        action_layout.addWidget(self.submit_button)
        left_layout.addLayout(action_layout)

        left_layout.addWidget(self.hint_view)

        self.section_route_view.add_widget(self.route_view)
        left_layout.addWidget(self.section_route_view)

        self.top_view.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        left_layout.setAlignment(Qt.AlignTop)

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
        self.schedule.save('save_exchanges')

    def run_schedule(self):
        print('run_schedule')
        self.section_middle.switch_content(False)
        self.section_route_view.switch_content(True)
        try:
            exchanges = {}
            for group in self.middle_view.item_groups:
                island = group.island_combobox.currentText()
                source = group.item_combobox_source.currentText()
                target = group.item_combobox_target.currentText()
                ratio = group.ratio_input.value()
                amount = group.amount_input.value()
                if amount:
                    self.stock.update_trade_items(source, amount)
                swap_cost = group.swap_cost_input.value()
                exchanges[island] = (source, target, ratio, swap_cost, group.remain_trades)

            self.worker = Worker(exchanges, self.schedule)
            self.worker.finished.connect(self.submit_button_signal.emit)
            self.worker.start()
            self.route_view.start_loading()
        except Exception as e:
            logging.exception(e)
        print('run_schedule end')

    def closeEvent(self, a0):
        self.stock.save()
        a0.accept()

# 善用 networkx，路線相關的幾乎都能用吧?
# 檢查演算法
# 優化演算法


# 已處理
# 伊利 > 庭貝 > 奧眼得算一船負重
# add item option會跳出來
# 材料交換


# 烏鴉幣 突發交換
# normal 數量input
# 刪除交換
# 清除交換


# 輸入剩餘 swap cost
# 沒交換玩繼續交換 (route view勾勾自動更新middle)

# 一趟島順序順了沒?


# 看要不要加stock不足排除路線
# UI 醜死了
# schedule 中要不能操作
