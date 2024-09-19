import logging

from PyQt5 import QtCore
from PyQt5.QtCore import Qt

from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QApplication, QVBoxLayout, QPushButton, QHBoxLayout, QSizePolicy
)

from Scheduler import Scheduler
from UI.UI_schedule import TopWidget, MiddleWidget, RouteViewWidget, HintWidget
from UI.UI_stock import StockWidget
from UI.UI_widget import FileChooser, Worker, CollapsibleSection, WidgetView
from utility import resource_path


class MainWindow(WidgetView):
    submit_button_signal = QtCore.pyqtSignal(list)
    upload_exchange_signal = QtCore.pyqtSignal(str)

    def __init__(self, island_graph, stock):
        super(MainWindow, self).__init__()

        try:
            self.setWindowTitle("Island Trade")
            self.setWindowIcon(QIcon(resource_path('static/icon.ico')))
            self.resize(1200, 900)
            self.set_font()
            self.set_theme()

            self.stock = stock
            self.island_graph = island_graph
            self.islands = sorted(list(island_graph.island_group_map.keys()))
            self.schedule = Scheduler(self.stock, self.island_graph)

            main_layout = QHBoxLayout(self)

            self.section_middle = CollapsibleSection()
            self.section_route_view = CollapsibleSection(False)

            self.top_view = TopWidget(self.stock, self.schedule)
            self.middle_view = MiddleWidget(self.islands, self.stock, self.schedule)
            self.hint_view = HintWidget(self.stock)
            self.route_view = RouteViewWidget(self.stock, self.schedule)

            self.clean_button = QPushButton("Clean")
            self.clean_button.clicked.connect(self.middle_view.clean_view)

            self.submit_button = QPushButton("Submit")
            self.submit_button.clicked.connect(self.run_schedule)
            self.submit_button_signal.connect(self.route_view.update_routes)
            self.submit_button_signal.connect(self.hint_view.generate_hints)

            self.save_exchange_button = QPushButton("Save Exchange")
            self.save_exchange_button.clicked.connect(self.save_exchange)

            self.save_remain_exchange_button = QPushButton("Save Remain Exchange")
            self.save_remain_exchange_button.clicked.connect(self.schedule.save_exchanges_remain)

            left_layout = self.add_left_area()

            self.stock_view = StockWidget(self.stock)
            right_layout = self.add_stock_view()

            main_layout.addLayout(left_layout, 1)
            main_layout.addLayout(right_layout, 1)

            self.route_view.stock_update_signal.connect(self.stock_view.update_items)
            self.route_view.income_update_signal.connect(self.top_view.update_income)
            self.top_view.add_item_signal.connect(self.middle_view.update_item_options)
            self.upload_exchange_signal.connect(self.middle_view.add_item_by_file)
            self.middle_view.upload_total_swap_cost_signal.connect(self.top_view.update_total_swap_cost)
            self.route_view.route_updated_signal.connect(self.enabled_view)

        except Exception as e:
            logging.exception(e)

    def add_left_area(self):
        left_layout = QVBoxLayout(self)
        self.setLayout(left_layout)

        left_layout.addWidget(self.top_view)

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
        try:
            self.update_exchanges()
            self.schedule.save_exchanges_all('save_exchanges')
        except Exception as e:
            logging.exception(e)

    def enabled_view(self, is_enabled):
        self.top_view.setEnabled(is_enabled)
        self.middle_view.setEnabled(is_enabled)
        self.route_view.setEnabled(is_enabled)
        self.stock_view.setEnabled(is_enabled)
        self.setEnabled(is_enabled)

    def update_exchanges(self):
        exchanges = {}
        for group in self.middle_view.exchange_settings:
            island = group.island_combobox.currentText()
            source = group.item_combobox_source.currentText()
            target = group.item_combobox_target.currentText()
            ratio = group.ratio_input.value()
            amount = group.amount_input.value()
            if amount:
                self.stock.update_trade_items(source, amount)
            swap_cost = group.swap_cost_input.value()
            exchanges[island] = (source, target, ratio, swap_cost, group.remain_trades)
        self.schedule.add_trade(exchanges)

    def run_schedule(self):
        try:
            self.enabled_view(False)
            self.section_middle.switch_content(False)
            self.section_route_view.switch_content(True)

            self.update_exchanges()
            self.worker = Worker(self.schedule)
            self.worker.finished.connect(self.submit_button_signal.emit)
            self.worker.start()
            self.route_view.start_loading()
        except Exception as e:
            logging.exception(e)

    def closeEvent(self, a0):
        self.schedule.save_settings()
        self.stock.save()
        a0.accept()
