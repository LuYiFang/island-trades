import logging

from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QSizePolicy, QLineEdit, QComboBox, \
    QPushButton, QCheckBox, QSpacerItem, QGroupBox

from UI_widget import ScrollableWidget, ItemGroup, Station, PlotDrawer
from exchange_items import default_ship_load_capacity, default_remain_swap_cost
from utility import read_json


class TopWidget(QWidget):
    add_item_signal = QtCore.pyqtSignal(str, object)

    def __init__(self, stock, schedule):
        super().__init__()

        self.stock = stock
        self.schedule = schedule

        self.load_input = None
        self.swap_cost_input = None
        self.checkbox = None
        self.add_button = None
        self.level_combobox = None
        self.item_input = None
        self.income_count_label = None
        self.layout = QVBoxLayout(self)

        self.add_island_graph()
        self.add_load_layout()
        self.add_remain_swap_cost_layout()
        self.add_new_item_layout()
        self.add_auto_sell_layout()
        self.setLayout(self.layout)

    def add_island_graph(self):
        layout = QHBoxLayout(self)
        island_graph = PlotDrawer('Island Graph', self.schedule.island_graph)
        island_group = PlotDrawer('Island Group', self.schedule.island_graph)
        group_graph = PlotDrawer('Group Graph', self.schedule.island_graph)
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

    def add_remain_swap_cost_layout(self):
        swap_cost_layout = QHBoxLayout(self)
        swap_cost_label = QLabel('Remain swap cost: ')
        self.swap_cost_input = QSpinBox()
        self.swap_cost_input.setRange(0, 1000000)
        self.swap_cost_input.setValue(default_remain_swap_cost)

        self.swap_cost_input.valueChanged.connect(self.on_swap_cost_value_changed)

        swap_cost_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.swap_cost_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        swap_cost_layout.addWidget(swap_cost_label)
        swap_cost_layout.addWidget(self.swap_cost_input)

        self.layout.addLayout(swap_cost_layout)

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
        self.checkbox.setChecked(True)
        label = QLabel('Auto Sell')
        self.checkbox.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        spacer = QSpacerItem(10, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
        check_layout.addWidget(self.checkbox)
        check_layout.addItem(spacer)
        check_layout.addWidget(label)

        income_label = QLabel('收入: ')
        self.income_count_label = QLabel('')
        check_layout.addWidget(income_label)
        check_layout.addWidget(self.income_count_label)
        income_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.income_count_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.checkbox.stateChanged.connect(self.on_checkbox_changed)
        self.layout.addLayout(check_layout)

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
        self.schedule.ship_load_capacity = self.load_input.value()

    def on_swap_cost_value_changed(self):
        self.schedule.total_swap_cost = self.load_input.value()

    def update_total_swap_cost(self, remain_swap_cost):
        self.swap_cost_input.setValue(remain_swap_cost)

    def update_income(self, income):
        self.income_count_label.setText(f'{income:,}')


class MiddleWidget(ScrollableWidget):
    def __init__(self, islands, stock, upload_total_swap_cost_signal):
        super(MiddleWidget, self).__init__()

        self.islands = islands
        self.stock = stock
        self.upload_total_swap_cost_signal = upload_total_swap_cost_signal
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

    def add_item_group(self, island=None, source=None, target=None, ratio=None, swap_cost=None, remain_trades=None):
        group = ItemGroup(self.islands, self.stock, island, source, target, ratio, swap_cost, remain_trades)
        self.item_groups.append(group)
        self.add_widget_to_scroll(group)
        return group

    def add_item_by_file(self, filename):
        try:
            self.clean_view()

            data = read_json(filename)
            if 'remain_swap_cost' in data:
                remain_swap_cost = data.pop('remain_swap_cost')
                self.upload_total_swap_cost_signal.emit(remain_swap_cost)

            for i, (island, info) in enumerate(data.items()):
                self.add_item_group(
                    island, info['source'], info['target'], info['ratio'],
                    info['swap_cost'], info.get('remain_trades')
                )
        except Exception as e:
            logging.exception(e)

    def update_item_options(self, item, level):
        try:
            for group in self.item_groups:
                group.item_combobox_source.update_option(item, level)
                group.item_combobox_target.update_option(item, level)
        except Exception as e:
            logging.exception(e)

    def clean_view(self):
        for item in self.item_groups:
            if item is not None:
                item.deleteLater()
        self.item_groups = []


class RouteViewWidget(ScrollableWidget):
    def __init__(self, stock, schedule, stock_update_signal, income_update_signal):
        super().__init__()

        self.stock = stock
        self.schedule = schedule
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
                    self.schedule,
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

    def add_route_by_file(self, filename):
        data = read_json(filename)
        for i, (island, info) in enumerate(data.items()):
            self.add_item_group(island, info['source'], info['target'], info['ratio'])
