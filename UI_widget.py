import logging
import re

from PyQt5 import QtCore
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFileDialog, QScrollArea, QComboBox, QHBoxLayout, \
    QSpinBox, QLabel, QCheckBox, QToolButton, QFrame, QTextEdit, QSizePolicy

from Scheduler import Scheduler
from exchange_items import default_amount


class FileChooser(QWidget):
    def __init__(self, title, upload_exchange_signal):
        super().__init__()

        self.upload_exchange_signal = upload_exchange_signal

        layout = QVBoxLayout()

        self.button = QPushButton(title, self)
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

    def __init__(self, exchanges, schedule):
        super(Worker, self).__init__()
        self.exchanges = exchanges
        self.schedule = schedule

    def run(self):
        try:
            self.schedule.add_trade(self.exchanges)
            routes = self.schedule.schedule_routes()
            self.finished.emit(routes)
        except Exception as e:
            logging.exception(e)


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

        main_layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(main_layout)

    def add_widget_to_scroll(self, widget):
        self.layout.addWidget(widget)

    def insert_widget_to_scroll(self, index, widget):
        self.layout.insertWidget(index, widget)

    def add_layout_to_scroll(self, layout):
        self.content_widget.setLayout(layout)

    def scroll_to_bottom(self):
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


class ColorComboBox(QComboBox):
    color_changed = QtCore.pyqtSignal(list)

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
        self.currentIndexChanged.connect(self.index_update_background)

    def init_options(self):
        for i, (level, color) in enumerate(self.color_dict.items()):
            for j, item_info in enumerate(self.stock.trade_items.get(level, [])):
                self.addItem(f'{item_info["name"]}')
                self.setItemData(self.count() - 1, color, Qt.BackgroundRole)
                self.setItemData(self.count() - 1, QColor(25, 25, 25), Qt.ForegroundRole)
                if i == j == 0:
                    self.update_background(self.currentIndex(), False)

    def update_option(self, item, level):
        self.insertItem(0, item)
        self.setItemData(0, self.color_dict[level], Qt.BackgroundRole)

    def index_update_background(self, index):
        self.update_background(index, True)

    def update_background(self, index, popup=True):
        color = self.itemData(index, Qt.BackgroundRole)
        self.setStyleSheet(f"QComboBox {{ background-color: {color.name()}; color: black; }}")

        text = self.itemData(index, Qt.DisplayRole)
        level = self.stock.item_level[text]
        self.color_changed.emit([level, text, popup])


class ItemGroup(QWidget):
    def __init__(self, islands, stock, *default_values):
        super(ItemGroup, self).__init__()

        self.stock = stock

        layout = QHBoxLayout()

        try:

            island, source, target, ratio, swap_cost, self.remain_trades = None, None, None, None, None, None
            if default_values:
                island, source, target, ratio, swap_cost, self.remain_trades = default_values

            self.island_combobox = QComboBox()
            self.island_combobox.setEditable(True)
            self.island_combobox.addItems(islands)
            if island is not None:
                self.island_combobox.setCurrentText(island)

            self.item_combobox_source = ColorComboBox(stock)
            if source is not None:
                self.item_combobox_source.setCurrentText(source)

            self.item_combobox_target = ColorComboBox(stock)
            if target is not None:
                self.item_combobox_target.setCurrentText(target)

            self.ratio_input = QSpinBox()
            self.ratio_input.setRange(0, 100)
            if ratio is not None:
                self.ratio_input.setValue(ratio)

            self.amount_input = QSpinBox()
            self.amount_input.setRange(0, 10000)
            self.amount_input.setValue(default_amount)

            amount = self.stock.item_info.get(source, {}).get('amount')
            if source is not None and amount:
                self.amount_input.setValue(amount)

            self.swap_cost_input = QSpinBox()
            self.swap_cost_input.setRange(0, 100000)
            self.swap_cost_input.setValue(11220)
            if swap_cost is not None:
                self.ratio_input.setValue(swap_cost)

            layout.addWidget(self.island_combobox, 2)
            layout.addWidget(self.item_combobox_source, 3)
            layout.addWidget(self.item_combobox_target, 3)
            layout.addWidget(self.ratio_input, 1)
            layout.addWidget(self.amount_input, 1)
            layout.addWidget(self.swap_cost_input, 1)

            self.setLayout(layout)

            if default_values:
                self.update_default_quantity([stock.item_level.get(source, 'normal'), source, False])
            else:
                self.update_default_quantity(['normal', self.stock.trade_items['normal'][0], False])

            self.item_combobox_source.color_changed.connect(self.update_default_quantity)
        except Exception as e:
            logging.exception(e)

    def update_default_quantity(self, params):
        level, item, popup = params
        if level == 'normal' or level == 4:
            self.ratio_input.setValue(1)
        elif level == 1 or level == 2:
            self.ratio_input.setValue(3)
        elif level == 3 or level == 5:
            self.ratio_input.setValue(2)

        default_amount = self.stock.item_info.get(item, {}).get('amount')
        if default_amount:
            self.amount_input.setValue(default_amount)

        if not popup:
            return

        visible_items_count = 10
        count = 0
        for _level in self.item_combobox_target.color_dict.keys():
            items = self.stock.trade_items[_level]
            if _level != level:
                count += len(items)
                continue
            count += len(items)
            break
        self.item_combobox_target.showPopup()

        def check_and_scroll():
            if self.item_combobox_target.view().isVisible():
                self.item_combobox_target.view().scrollTo(
                    self.item_combobox_target.model().index(count + visible_items_count - 1, 0)
                )
                return
            QTimer.singleShot(100, check_and_scroll)

        check_and_scroll()


class Station(QWidget):
    def __init__(self, exchange, num, stock, schedule: Scheduler, stock_update_signal, income_update_signal):
        super(Station, self).__init__()

        self.stock = stock
        self.schedule = schedule
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
        layout.addWidget(QLabel(f": {num}"))
        layout.addWidget(QLabel(" -> "))
        layout.addWidget(label_b)
        layout.addWidget(QLabel(exchange.target))
        self.setLayout(layout)

    def on_checkbox_changed(self, state):
        self.stock.switch_stock(False)

        try:
            if state == Qt.Unchecked:
                self.schedule.undo_execute_exchange(self.exchange, self.trades, id(self))
            else:
                self.schedule.execute_exchange(self.exchange, self.trades, id(self))

            self.stock_update_signal.emit([self.exchange.source, self.exchange.target])
            self.income_update_signal.emit(self.stock.count_income())

        except Exception as e:
            logging.exception(e)


class CollapsibleSection(QWidget):
    def __init__(self, is_open=True):
        super().__init__()
        self.layout = QVBoxLayout()

        self.toggle_button = QToolButton(checkable=True, checked=True)
        self.toggle_button.setStyleSheet("QToolButton { border: none; }")
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.clicked.connect(self.toggle_content)
        self.toggle_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.toggle_button.setContentsMargins(0, 0, 0, 0)

        self.content_frame = QFrame()
        self.content_frame.setContentsMargins(0, 0, 0, 0)
        self.content_frame_layout = QVBoxLayout()
        self.content_frame_layout.setContentsMargins(0, 0, 0, 0)

        self.layout.addWidget(self.toggle_button, alignment=Qt.AlignTop | Qt.AlignLeft)

        self.content_frame.setLayout(self.content_frame_layout)
        self.layout.addWidget(self.content_frame)

        self.layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)

        if is_open:
            self.content_frame.show()
            self.toggle_button.setArrowType(Qt.DownArrow)
        else:
            self.toggle_button.setArrowType(Qt.RightArrow)
            self.content_frame.hide()

    def toggle_content(self):
        self.switch_content(self.toggle_button.isChecked())

    def switch_content(self, is_open):
        if is_open:
            self.toggle_button.setArrowType(Qt.DownArrow)
            self.content_frame.show()
        else:
            self.toggle_button.setArrowType(Qt.RightArrow)
            self.content_frame.hide()

    def add_widget(self, widget, *args):
        self.content_frame_layout.addWidget(widget, *args)
