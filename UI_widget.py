import logging
import re

from PyQt5 import QtCore
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFileDialog, QScrollArea, QComboBox, QHBoxLayout, \
    QSpinBox, QLabel, QCheckBox


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


class PlotDrawer(QWidget):
    def __init__(self, title, island_graph):
        super().__init__()

        self.island_graph = island_graph
        self.title = title

        self.setWindowTitle(title)

        layout = QVBoxLayout()

        self.button = QPushButton(title, self)
        self.button.clicked.connect(self.show_plot)
        layout.addWidget(self.button)

        self.setLayout(layout)

    def show_plot(self):
        func_name = re.sub(
            r'([A-Z][a-z]+)\s+([A-Z][a-z]+)',
            lambda m: f"{m.group(1).lower()}_{m.group(2).lower()}", self.title)
        getattr(self.island_graph, f'draw_{func_name}')()


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


class ColorComboBox(QComboBox):
    color_changed = QtCore.pyqtSignal(object)

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

        self.stock = stock

        layout = QHBoxLayout()

        self.island_combobox = QComboBox()
        self.island_combobox.setEditable(True)
        self.island_combobox.addItems(islands)

        self.item_combobox_source = ColorComboBox(stock)
        self.item_combobox_target = ColorComboBox(stock)

        self.ratio_input = QSpinBox()
        self.ratio_input.setRange(0, 100)

        self.swap_cost_input = QSpinBox()
        self.swap_cost_input.setRange(0, 100000)
        self.swap_cost_input.setValue(11260)

        layout.addWidget(self.island_combobox, 2)
        layout.addWidget(self.item_combobox_source, 3)
        layout.addWidget(self.item_combobox_target, 3)
        layout.addWidget(self.ratio_input, 1)
        layout.addWidget(self.swap_cost_input, 1)

        self.setLayout(layout)

        self.update_default_quantity('normal')

        self.item_combobox_source.color_changed.connect(self.update_default_quantity)

    def update_default_quantity(self, level):
        popup_height = self.item_combobox_target.view().height()
        item_height = self.item_combobox_target.view().sizeHintForRow(0)
        visible_items_count = popup_height // item_height

        count = 0
        for _level in self.item_combobox_target.color_dict.keys():
            items = self.stock.trade_items[_level]
            if _level != level:
                count += len(items)
                continue
            count += len(items)
            break
        self.item_combobox_target.showPopup()
        self.item_combobox_target.view().scrollTo(
            self.item_combobox_target.model().index(count + visible_items_count - 1, 0)
        )

        if level == 'normal' or level == 4:
            self.ratio_input.setValue(1)
            return
        if level == 1 or level == 2:
            self.ratio_input.setValue(3)
            return
        if level == 3:
            self.ratio_input.setValue(2)


class Station(QWidget):
    def __init__(self, exchange, num, stock, stock_update_signal, income_update_signal):
        super(Station, self).__init__()

        self.stock = stock
        self.exchange = exchange
        self.trades = num
        self.stock_update_signal = stock_update_signal
        self.income_update_signal = income_update_signal

        image_path_a = f"static/{exchange.source_img}"
        image_path_b = f"static/{exchange.target_img}"

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
        layout.addWidget(QLabel(exchange.island))
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
