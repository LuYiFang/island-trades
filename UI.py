import functools
import logging

from PyQt5 import QtCore

from PyQt5.QtCore import QStringListModel, Qt
from PyQt5.QtGui import QPalette, QColor, QFont, QStandardItemModel, QStandardItem, QBrush, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit,
    QComboBox, QCheckBox, QVBoxLayout, QPushButton, QFormLayout, QSpinBox, QScrollArea, QHBoxLayout, QGroupBox,
    QListWidget, QListWidgetItem, QMainWindow, QListView, QGridLayout, QSizePolicy, QSpacerItem, QFileDialog,
)
from PyQt5.QtCore import QThread, pyqtSignal

from Exchange import ExchangeGraph
from exchange_items import default_ship_load_capacity
from utility import read_json


class FileChooser(QWidget):
    def __init__(self, upload_exchange_signal):
        super().__init__()

        self.upload_exchange_signal = upload_exchange_signal
        self.setWindowTitle('File Chooser Example')

        layout = QVBoxLayout()

        self.button = QPushButton('Open Exchanges File', self)
        self.button.clicked.connect(self.show_dialog)
        layout.addWidget(self.button)

        self.setLayout(layout)

    def show_dialog(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(self, "Open JSON File",
                                                  "storage",
                                                  "JSON Files (*.json);;All Files (*)",
                                                  options=options)
        if filename:
            self.upload_exchange_signal.emit(filename)


class Worker(QThread):
    finished = pyqtSignal(list)

    def __init__(self, exchanges, exchange_graph):
        super(Worker, self).__init__()
        self.exchanges = exchanges
        self.exchange_graph = exchange_graph

    def run(self):
        self.exchange_graph.add_trade(self.exchanges)
        routes = self.exchange_graph.schedule_routes()
        self.finished.emit(routes)


class ScrollableWidget(QWidget):
    def __init__(self):
        super(ScrollableWidget, self).__init__()

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)

        self.content_widget = QWidget(self)
        self.scroll_area.setWidget(self.content_widget)

        self.layout = QVBoxLayout(self.content_widget)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.scroll_area)

        self.setLayout(main_layout)

    def add_widget_to_scroll(self, widget):
        self.layout.addWidget(widget)

    def insert_widget_to_scroll(self, index, widget):
        self.layout.insertWidget(index, widget)

    def add_layout_to_scroll(self, layout):
        self.content_widget.setLayout(layout)


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

        self.add_load_layout()
        self.add_new_item_layout()
        self.add_auto_sell_layout()
        self.add_income_layout()
        self.setLayout(self.layout)

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


class ColorComboBox(QComboBox):
    color_changed = QtCore.pyqtSignal(int)

    def __init__(self, stock):
        super().__init__()

        self.stock = stock

        self.color_dict = {
            "normal": QColor(255, 247, 217),
            1: QColor(161, 161, 161),
            2: QColor(109, 132, 17),
            3: QColor(64, 150, 193),
            4: QColor(170, 130, 63),
            5: QColor(209, 103, 90),
            "material": QColor(105, 90, 209)
        }

        self.init_options()
        self.currentIndexChanged.connect(self.update_background)

    def init_options(self):
        for level, color in self.color_dict.items():
            for item_info in self.stock.trade_items.get(level, []):
                self.addItem(f'{item_info["name"]}')
                self.setItemData(self.count() - 1, color, Qt.BackgroundRole)
                self.setItemData(self.count() - 1, QColor(25, 25, 25), Qt.ForegroundRole)

        self.update_background(self.currentIndex())

    def update_option(self, item, level):
        self.insertItem(0, item)
        self.setItemData(0, self.color_dict[level], Qt.BackgroundRole)

    def update_background(self, index):
        color = self.itemData(index, Qt.BackgroundRole)
        self.setStyleSheet(f"QComboBox {{ background-color: {color.name()}; color: black; }}")

        text = self.itemData(index, Qt.DisplayRole)
        level = self.stock.item_level[text]
        self.color_changed.emit(level)


class ItemGroup(QWidget):
    def __init__(self, islands, stock):
        super(ItemGroup, self).__init__()

        layout = QHBoxLayout()

        self.island_combobox = QComboBox()
        self.island_combobox.addItems(islands)

        self.item_combobox_source = ColorComboBox(stock)
        self.item_combobox_target = ColorComboBox(stock)

        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(0, 100)

        self.swap_cost_input = QSpinBox()
        self.swap_cost_input.setRange(0, 100000)
        self.swap_cost_input.setValue(11485)

        self.specified_quantity_input = QSpinBox()
        self.specified_quantity_input.setRange(0, 100)

        layout.addWidget(self.island_combobox, 2)
        layout.addWidget(self.item_combobox_source, 3)
        layout.addWidget(self.item_combobox_target, 3)
        layout.addWidget(self.quantity_input, 1)
        layout.addWidget(self.specified_quantity_input, 1)
        layout.addWidget(self.swap_cost_input, 1)

        self.setLayout(layout)

        self.update_default_quantity('normal')

        self.item_combobox_source.color_changed.connect(self.update_default_quantity)

    def update_default_quantity(self, level):
        if level == 'normal' or level == 4:
            self.quantity_input.setValue(1)
            return
        if level == 1 or level == 2:
            self.quantity_input.setValue(3)
            return
        if level == 3:
            self.quantity_input.setValue(2)


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
        header_layout.addWidget(QLabel('Trade'), 1)
        header_layout.addWidget(QLabel('Swap Cost'), 1)
        self.add_layout_to_scroll(header_layout)

        header_widget = QWidget()
        header_widget.setLayout(header_layout)
        self.add_widget_to_scroll(header_widget)

        self.layout.setAlignment(Qt.AlignTop)

        self.add_item_button.clicked.connect(self.add_item_group)

    def create_item_group(self):
        group = ItemGroup(self.islands, self.stock)
        self.item_groups.append(group)
        return group

    def add_item_group(self):
        group = self.create_item_group()
        self.add_widget_to_scroll(group)
        return group

    def add_item_by_file(self, filename):
        data = read_json(filename)
        for i, (island, info) in enumerate(data.items()):
            group = self.add_item_group()
            group.island_combobox.setCurrentText(island)
            group.item_combobox_source.setCurrentText(info['source'])
            group.item_combobox_target.setCurrentText(info['target'])
            group.quantity_input.setValue(info['ratio'])

    def update_item_options(self, item, level):
        try:
            for group in self.item_groups:
                group.item_combobox_source.update_option(item, level)
                group.item_combobox_target.update_option(item, level)
        except Exception as e:
            logging.exception(e)


class Route(QWidget):
    def __init__(self, island, exchange, num, stock, stock_update_signal, income_update_signal):
        super(Route, self).__init__()

        self.stock = stock
        self.exchange = exchange
        self.trades = num
        self.stock_update_signal = stock_update_signal
        self.income_update_signal = income_update_signal

        image_path_a = "static/玫瑰.png"
        image_path_b = "static/玫瑰.png"

        pixmap_a = QPixmap(image_path_a).scaled(20, 20)
        pixmap_b = QPixmap(image_path_b).scaled(20, 20)

        label_a = QLabel()
        label_a.setPixmap(pixmap_a)

        label_b = QLabel()
        label_b.setPixmap(pixmap_b)

        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(self.on_checkbox_changed)

        layout = QHBoxLayout()
        layout.addWidget(self.checkbox)
        layout.addWidget(QLabel(island))
        layout.addWidget(label_a)
        layout.addWidget(QLabel(exchange.source))
        layout.addWidget(QLabel(" -> "))
        layout.addWidget(label_b)
        layout.addWidget(QLabel(exchange.target))
        layout.addWidget(QLabel(f": {num}"))
        self.setLayout(layout)

    def on_checkbox_changed(self, state):
        self.stock.switch_stock(False)

        if state == Qt.Unchecked:
            self.stock.undo_execute_exchange(self.exchange, self.trades, id(self))
        else:
            self.stock.execute_exchange(self.exchange, self.trades, id(self))

        self.stock_update_signal.emit([self.exchange.source, self.exchange.target])
        self.income_update_signal.emit(self.stock.count_income())


class RouteViewWidget(ScrollableWidget):
    def __init__(self, stock, stock_update_signal, income_update_signal):
        super().__init__()

        self.stock = stock
        self.stock_update_signal = stock_update_signal
        self.income_update_signal = income_update_signal

        self.route_list = []
        self.group_list = []

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
        for i, route_path in enumerate(routes):
            group_name = f'group_{i}'
            group = QGroupBox(group_name)
            group_layout = QVBoxLayout(group)

            self.group_list.append(group)

            for island, (exchange, trades) in route_path.items():
                route = Route(
                    island,
                    exchange,
                    trades,
                    self.stock,
                    self.stock_update_signal,
                    self.income_update_signal
                )
                group_layout.addWidget(route)

                self.add_widget_to_scroll(group)
                self.route_list.append(route)

        self.stop_loading()

    def clean_view(self):
        for group in self.group_list:
            if group is not None:
                group.deleteLater()
        self.group_list = []

        for route in self.route_list:
            if route is not None:
                route.deleteLater()
        self.route_list = []


class StockWidget(ScrollableWidget):
    def __init__(self, stock):
        super().__init__()

        self.stock = stock

        self.item_counts = {}
        self.item_spin_boxes = {}
        self.modify_count_text = 'Edit'
        self.confirm_count_text = 'Confirm'

        self.button_modify = QPushButton(self.modify_count_text)
        self.build_item_grid()

    def update_items(self, item_list):
        for key in item_list:
            if not self.item_counts.get(key):
                continue
            self.item_counts[key].setText(f'{self.stock[key]}')
            self.item_spin_boxes[key][1].setValue(self.stock[key])

    def build_item_grid(self):
        self.stock.switch_stock(False)
        for level, item_list in self.stock.trade_items.items():
            if not isinstance(level, int):
                continue

            groupbox = QGroupBox(f"Level {level}")
            grid_layout = QGridLayout()
            for item_index, item in enumerate(item_list):
                image_path = f"static/{item['img']}"

                label_image = QLabel()
                pixmap = QPixmap(image_path).scaled(50, 50)
                label_image.setPixmap(pixmap)

                item_name = item['name']
                item_count = self.stock[item['name']]
                label_item = QLabel(f"{item_name}")
                label_count = QLabel(f"{item_count}")

                quantity_label = QLabel('Qty')
                quantity_input = QSpinBox()
                quantity_input.setRange(0, 1000)
                quantity_input.setValue(item_count)

                quantity_count = self.stock.reserved_quantity[item['name']]
                reserved_label = QLabel('Res.')
                reserved_quantity_input = QSpinBox()
                reserved_quantity_input.setRange(0, 1000)
                reserved_quantity_input.setValue(quantity_count)

                vbox_layout = QVBoxLayout()
                vbox_layout.addWidget(label_item)
                vbox_layout.addWidget(label_count)

                quantity_layout = QHBoxLayout()
                quantity_layout.addWidget(quantity_label)
                quantity_layout.addWidget(quantity_input)
                vbox_layout.addLayout(quantity_layout)

                reserved_layout = QHBoxLayout()
                reserved_layout.addWidget(reserved_label)
                reserved_layout.addWidget(reserved_quantity_input)
                vbox_layout.addLayout(reserved_layout)

                quantity_label.hide()
                quantity_input.hide()
                reserved_label.hide()
                reserved_quantity_input.hide()

                vbox_layout.addStretch()

                hbox_layout = QHBoxLayout()
                hbox_layout.addWidget(label_image)
                hbox_layout.addLayout(vbox_layout)

                row = item_index // 8
                col = item_index % 8

                grid_layout.addLayout(hbox_layout, row, col)

                self.item_counts[item_name] = label_count
                self.item_spin_boxes[item_name] = (
                    quantity_label, quantity_input, reserved_label, reserved_quantity_input)

            groupbox.setLayout(grid_layout)

            self.add_widget_to_scroll(groupbox)

        self.button_modify.clicked.connect(self.on_modify_button_clicked)
        self.add_widget_to_scroll(self.button_modify)

    def on_modify_button_clicked(self):
        if self.button_modify.text() == self.modify_count_text:
            self.show_spin_boxes()
            self.button_modify.setText(self.confirm_count_text)
            return

        self.confirm_count()
        self.button_modify.setText(self.modify_count_text)

    def show_spin_boxes(self):
        for key, (
                quantity_label, quantity_input, reserved_label,
                reserved_quantity_input) in self.item_spin_boxes.items():
            self.item_counts[key].hide()
            quantity_label.show()
            quantity_input.show()
            reserved_label.show()
            reserved_quantity_input.show()

    def confirm_count(self):
        self.stock.switch_stock(False)
        self.button_modify.setText(self.modify_count_text)
        for item_name, (
                quantity_label, quantity_input, reserved_label,
                reserved_quantity_input) in self.item_spin_boxes.items():
            self.stock[item_name] = quantity_input.value()
            self.stock.reserved_quantity[item_name] = reserved_quantity_input.value()
            self.item_counts[item_name].setText(f'{self.stock[item_name]}')
            quantity_label.hide()
            quantity_input.hide()
            reserved_label.hide()
            reserved_quantity_input.hide()
            self.item_counts[item_name].show()


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
        self.exchange_graph = ExchangeGraph(self.stock, self.island_graph)

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
        self.exchange_graph.save('save_graph')

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

        self.worker = Worker(exchanges, self.exchange_graph)
        self.worker.finished.connect(self.submit_button_signal.emit)
        self.worker.start()
        self.route_view.start_loading()

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
