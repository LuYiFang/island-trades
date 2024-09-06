import logging

from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QSizePolicy, QLineEdit, QComboBox, \
    QPushButton, QCheckBox, QSpacerItem, QGroupBox

from UI_widget import ScrollableWidget, ItemGroup, Station, PlotDrawer
from exchange_items import default_ship_load_capacity
from utility import read_json


class TopWidget(QWidget):
    add_item_signal = QtCore.pyqtSignal(str, object)

    def __init__(self, stock, exchange_graph):
        super().__init__()

        self.stock = stock
        self.exchange_graph = exchange_graph

        self.load_input = None
        self.checkbox = None
        self.add_button = None
        self.level_combobox = None
        self.item_input = None
        self.income_count_label = None
        self.layout = QVBoxLayout(self)

        self.add_island_graph()
        self.add_load_layout()
        self.add_new_item_layout()
        self.add_auto_sell_layout()
        self.add_income_layout()
        self.setLayout(self.layout)

    def add_island_graph(self):
        layout = QHBoxLayout(self)
        island_graph = PlotDrawer('Island Graph', self.exchange_graph.island_graph)
        island_group = PlotDrawer('Island Group', self.exchange_graph.island_graph)
        group_graph = PlotDrawer('Group Graph', self.exchange_graph.island_graph)
        layout.addWidget(island_graph)
        layout.addWidget(island_group)
        layout.addWidget(group_graph)
        self.layout.addLayout(layout)

    def add_load_layout(self):
        load_layout = QHBoxLayout(self)
        load_label = QLabel('Ship Load Capacity: ')
        self.load_input = QSpinBox()
        self.load_input.setRange(0, 100000)
        self.load_input.setValue(default_ship_load_capacity)

        self.load_input.valueChanged.connect(self.on_load_value_changed)

        load_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.load_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        load_layout.addWidget(load_label)
        load_layout.addWidget(self.load_input)

        self.layout.addLayout(load_layout)

    def add_new_item_layout(self):
        new_item_layout = QHBoxLayout(self)
        self.item_input = QLineEdit()
        self.level_combobox = QComboBox()
        level_options = []
        for k in self.stock.trade_items.keys():
            if isinstance(k, int):
                level_options.append(f'level_{k}')
                continue
            level_options.append(k)
        self.level_combobox.addItems(level_options)
        self.add_button = QPushButton("Add")
        new_item_layout.addWidget(QLabel("New Item:"))
        new_item_layout.addWidget(self.item_input)
        new_item_layout.addWidget(QLabel("Level:"))
        new_item_layout.addWidget(self.level_combobox)
        new_item_layout.addWidget(self.add_button)

        self.add_button.clicked.connect(self.add_item)
        self.layout.addLayout(new_item_layout)

    def add_auto_sell_layout(self):
        check_layout = QHBoxLayout(self)
        self.checkbox = QCheckBox()
        label = QLabel('Auto Sell')
        self.checkbox.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        spacer = QSpacerItem(10, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
        check_layout.addWidget(self.checkbox)
        check_layout.addItem(spacer)
        check_layout.addWidget(label)

        self.checkbox.stateChanged.connect(self.on_checkbox_changed)
        self.layout.addLayout(check_layout)

    def add_income_layout(self):
        sell_layout = QHBoxLayout()
        income_label = QLabel('收入: ')
        self.income_count_label = QLabel('')
        sell_layout.addWidget(income_label)
        sell_layout.addWidget(self.income_count_label)
        income_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.income_count_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.layout.addLayout(sell_layout)

    def add_item(self):
        level = self.level_combobox.currentText().replace('level_', '')
        try:
            level = int(level)
        except:
            pass

        self.stock.update_trade_items(level, self.item_input.text())
        self.add_item_signal.emit(self.item_input.text(), level)
        self.item_input.setText('')

    def on_checkbox_changed(self, state):
        if state == Qt.Unchecked:
            self.stock.switch_auto_sell(False)
        else:
            self.stock.switch_auto_sell(True)

    def on_load_value_changed(self):
        self.exchange_graph.ship_load_capacity = self.load_input.value()

    def update_income(self, income):
        self.income_count_label.setText(f'{income:,}')


class MiddleWidget(ScrollableWidget):
    def __init__(self, islands, stock):
        super(MiddleWidget, self).__init__()

        self.islands = islands
        self.stock = stock
        self.item_groups = []

        self.add_item_button = QPushButton("+")
        self.add_widget_to_scroll(self.add_item_button)

        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel('Island'), 2)
        header_layout.addWidget(QLabel('Source'), 3)
        header_layout.addWidget(QLabel('Target'), 3)
        header_layout.addWidget(QLabel('Ratio'), 1)
        header_layout.addWidget(QLabel('Swap Cost'), 1)
        self.add_layout_to_scroll(header_layout)

        header_widget = QWidget()
        header_widget.setLayout(header_layout)
        self.add_widget_to_scroll(header_widget)

        self.layout.setAlignment(Qt.AlignTop)

        self.add_item_button.clicked.connect(self.button_add_item_group)

    def button_add_item_group(self):
        self.add_item_group()

    def add_item_group(self, island=None, source=None, target=None, ratio=None):
        group = ItemGroup(self.islands, self.stock, island, source, target, ratio)
        self.item_groups.append(group)
        self.add_widget_to_scroll(group)
        return group

    def add_item_by_file(self, filename):
        data = read_json(filename)
        for i, (island, info) in enumerate(data.items()):
            self.add_item_group(island, info['source'], info['target'], info['ratio'])

    def update_item_options(self, item, level):
        try:
            for group in self.item_groups:
                group.item_combobox_source.update_option(item, level)
                group.item_combobox_target.update_option(item, level)
        except Exception as e:
            logging.exception(e)


class RouteViewWidget(ScrollableWidget):
    def __init__(self, stock, stock_update_signal, income_update_signal):
        super().__init__()

        self.stock = stock
        self.stock_update_signal = stock_update_signal
        self.income_update_signal = income_update_signal

        self.station_list = []
        self.group_list = []
        self.routes = []

        loading_layout = QHBoxLayout()
        self.loading = QLabel('Scheduling...')
        loading_layout.addStretch()
        loading_layout.addWidget(self.loading)
        loading_layout.addStretch()
        self.loading.hide()
        self.layout.addLayout(loading_layout)

    def start_loading(self):
        self.clean_view()
        self.loading.show()

    def stop_loading(self):
        self.loading.hide()

    def update_routes(self, routes):
        self.routes = routes

        for group_name, route in routes:
            group = QGroupBox(group_name)
            group_layout = QVBoxLayout(group)

            self.group_list.append(group)

            for exchange, trades in route:
                station = Station(
                    exchange,
                    trades,
                    self.stock,
                    self.stock_update_signal,
                    self.income_update_signal
                )
                group_layout.addWidget(station)

                self.add_widget_to_scroll(group)
                self.station_list.append(station)

        self.stop_loading()

    def clean_view(self):
        for group in self.group_list:
            if group is not None:
                group.deleteLater()
        self.group_list = []

        for route in self.station_list:
            if route is not None:
                route.deleteLater()
        self.station_list = []
