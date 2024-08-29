from PyQt5 import QtCore

from PyQt5.QtCore import QStringListModel, Qt
from PyQt5.QtGui import QPalette, QColor, QFont, QStandardItemModel, QStandardItem, QBrush, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit,
    QComboBox, QCheckBox, QVBoxLayout, QPushButton, QFormLayout, QSpinBox, QScrollArea, QHBoxLayout, QGroupBox,
    QListWidget, QListWidgetItem, QMainWindow, QListView, QGridLayout, QSizePolicy, QSpacerItem,
)

from Island import ExchangeGraph, Stock
from exchange_items import level_1_items, level_2_items, level_3_items, level_4_items, level_5_items

from PyQt5.QtCore import QThread, pyqtSignal


class Worker(QThread):
    finished = pyqtSignal(dict)

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
    def __init__(self):
        super().__init__()

        self.layout = QVBoxLayout(self)

        self.new_item_layout = QHBoxLayout(self)
        self.item_input = QLineEdit()
        self.color_combobox = QComboBox()
        self.color_combobox.addItems(["normal", "level 1", "level 2", "level 3", "level 4", "level 5"])
        self.add_button = QPushButton("Add")

        self.new_item_layout.addWidget(QLabel("New Item:"))
        self.new_item_layout.addWidget(self.item_input)
        self.new_item_layout.addWidget(QLabel("Level:"))
        self.new_item_layout.addWidget(self.color_combobox)
        self.new_item_layout.addWidget(self.add_button)

        self.check_layout = QHBoxLayout(self)
        checkbox = QCheckBox()
        label = QLabel('Auto Sell')

        checkbox.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        spacer = QSpacerItem(10, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)

        self.check_layout.addWidget(checkbox)
        self.check_layout.addItem(spacer)
        self.check_layout.addWidget(label)

        self.sell_layout = QHBoxLayout()
        income_label = QLabel('收入: ')
        income_count_label = QLabel('258,432,132')
        self.sell_layout.addWidget(income_label)
        self.sell_layout.addWidget(income_count_label)

        income_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        income_count_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.layout.addLayout(self.new_item_layout)
        self.layout.addLayout(self.check_layout)
        self.layout.addLayout(self.sell_layout)

        self.setLayout(self.layout)


class ColorComboBox(QComboBox):
    def __init__(self):
        super().__init__()

        self.color_dict = {
            "white": QColor(242, 234, 205),
            "gray": QColor(99, 99, 98),
            "green": QColor(30, 132, 0),
            "blue": QColor(33, 63, 209),
            "yellow": QColor(217, 185, 2),
            "red": QColor(219, 58, 37),
            "purple": QColor(117, 39, 219)
        }

        for level, (color_name, color) in enumerate(self.color_dict.items()):
            for i in range(5):
                self.addItem(f'{level} - item{i}')
                self.setItemData(self.count() - 1, color, Qt.BackgroundRole)

        self.currentIndexChanged.connect(self.update_background)
        self.update_background(self.currentIndex())

    def update_background(self, index):
        color = self.itemData(index, Qt.BackgroundRole)
        self.setStyleSheet(f"QComboBox {{ background-color: {color.name()}; color: white; }}")


class ItemGroup(QWidget):
    def __init__(self, islands):
        super(ItemGroup, self).__init__()

        layout = QHBoxLayout()
        options = level_1_items + level_2_items + level_3_items + level_4_items + level_5_items

        self.island_combobox = QComboBox()
        self.island_combobox.addItems(islands)

        self.item_combobox_source = ColorComboBox()
        # self.item_combobox_source.addItems(options)

        self.item_combobox_target = ColorComboBox()
        self.item_combobox_target.addItems(options)

        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(0, 100)

        self.swap_cost_input = QSpinBox()
        self.swap_cost_input.setValue(11485)
        self.swap_cost_input.setRange(0, 10000)

        self.specified_quantity_input = QSpinBox()
        self.specified_quantity_input.setRange(0, 100)

        layout.addWidget(self.island_combobox, 2)
        layout.addWidget(self.item_combobox_source, 3)
        layout.addWidget(self.item_combobox_target, 3)
        layout.addWidget(self.quantity_input, 1)
        layout.addWidget(self.specified_quantity_input, 1)
        layout.addWidget(self.swap_cost_input, 1)

        self.setLayout(layout)


class MiddleWidget(ScrollableWidget):
    def __init__(self, islands):
        super(MiddleWidget, self).__init__()

        self.islands = islands
        self.item_groups = []

        self.add_item_button = QPushButton("+")
        self.add_widget_to_scroll(self.add_item_button)
        self.add_widget_to_scroll(self.create_item_group())

        self.layout.setAlignment(Qt.AlignTop)

        self.add_item_button.clicked.connect(self.add_item_group)

    def update_checkboxes(self, item_name, category, count):
        checkbox_label = QLabel(f"{item_name} - {category} ({count})")
        self.checkboxes_layout.addWidget(checkbox_label)

    def create_item_group(self):
        group = ItemGroup(self.islands)
        self.item_groups.append(group)
        return group

    def add_item_group(self):
        self.insert_widget_to_scroll(self.layout.count() - 1, self.create_item_group())


class Route(QWidget):
    def __init__(self, item_a, item_b, num):
        super(Route, self).__init__()

        image_path_a = "static/玫瑰.png"
        image_path_b = "static/玫瑰.png"

        # 創建圖片的QPixmap物件
        pixmap_a = QPixmap(image_path_a).scaled(20, 20)
        pixmap_b = QPixmap(image_path_b).scaled(20, 20)

        # 創建對應的QLabel來顯示圖片
        label_a = QLabel()
        label_a.setPixmap(pixmap_a)

        label_b = QLabel()
        label_b.setPixmap(pixmap_b)

        checkbox = QCheckBox()

        layout = QHBoxLayout()
        layout.addWidget(checkbox)
        layout.addWidget(label_a)
        layout.addWidget(QLabel(item_a))
        layout.addWidget(QLabel(" -> "))
        layout.addWidget(label_b)
        layout.addWidget(QLabel(item_b))
        layout.addWidget(QLabel(f": {num}"))
        self.setLayout(layout)

        self.add_item_button.clicked.connect(self.add_item_group)
        self.submit_button.clicked.connect(self.run_schedule)

        self.submit_button_signal.connect(self.update_checkboxes)


class DownWidget(ScrollableWidget):
    def __init__(self):
        super().__init__()

        self.route_list = []

    def update_routes(self, routes):
        print('update_routes')
        self.clean_view()

        for group_name, route_path in routes.items():
            group = QGroupBox(group_name)
            group_layout = QVBoxLayout(group)

            for island, exchange_info in route_path.items():
                route = Route(exchange_info['source'], exchange_info['target'], {exchange_info['exchange']})
                group_layout.addWidget(route)

                self.add_widget_to_scroll(group)
                self.route_list.append(route)

    def clean_view(self):
        for route in self.route_list:
            if route is not None:
                route.deleteLater()


class StockWidget(ScrollableWidget):
    def __init__(self):
        super().__init__()

        self.item_counts = []
        self.item_spin_boxes = []
        self.modify_count_text = 'Edit'
        self.confirm_count_text = 'Confirm'

        self.button_modify = QPushButton(self.modify_count_text)
        self.build_item_grid()

    def build_item_grid(self):
        for level in range(5):  # 每個階層框起來
            groupbox = QGroupBox(f"Level {level + 1}")
            grid_layout = QGridLayout()

            for item_index in range(15):  # 每階有15種物品
                # 提供圖片的路徑
                image_path = f"static/玫瑰.png"
                # 創建圖片的QPixmap物件，並調整大小
                pixmap = QPixmap(image_path).scaled(50, 50)

                # 創建對應的QLabel來顯示圖片
                label_image = QLabel()
                label_image.setPixmap(pixmap)

                # 創建物品名稱和數量的QLabel
                label_item = QLabel(f"屋屋啊{item_index + 1}")
                label_count = QLabel(f"{item_index * 2}")

                input_field = QSpinBox()
                input_field.setRange(0, 1000)
                input_field.setValue(item_index * 2)

                stock_quantity_input = QSpinBox()
                stock_quantity_input.setRange(0, 1000)
                stock_quantity_input.setValue(0)

                # 使用QVBoxLayout將物品名和數量疊加
                vbox_layout = QVBoxLayout()
                vbox_layout.addWidget(label_item)
                vbox_layout.addWidget(label_count)
                vbox_layout.addWidget(input_field)
                vbox_layout.addWidget(stock_quantity_input)
                input_field.hide()
                stock_quantity_input.hide()

                vbox_layout.addStretch()  # 讓物品名和數量疊起來，上下間距均衡

                # 將圖片和疊加的物品信息放在QHBoxLayout中
                hbox_layout = QHBoxLayout()
                hbox_layout.addWidget(label_image)
                hbox_layout.addLayout(vbox_layout)

                # 計算行列位置
                row = item_index // 8
                col = item_index % 8

                grid_layout.addLayout(hbox_layout, row, col)

                self.item_counts.append(label_count)
                self.item_spin_boxes.append((input_field, stock_quantity_input))

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
        for i, spins in enumerate(self.item_spin_boxes):
            self.item_counts[i].hide()
            spins[0].show()
            spins[1].show()

    def confirm_count(self):
        for i, spins in enumerate(self.item_spin_boxes):
            self.item_counts[i].show()
            spins[0].hide()
            spins[1].hide()


class MainWindow(QWidget):
    submit_button_signal = QtCore.pyqtSignal(dict)

    def __init__(self, island_graph):
        super(MainWindow, self).__init__()

        self.stock = Stock({
            '蓮花': 3,
            '豌豆': 5,
            '櫻花': 2,
        })

        self.island_graph = island_graph
        self.islands = list(island_graph.island_group_map.keys())
        self.exchange_graph = ExchangeGraph('A', 11500, self.stock, self.island_graph)

        self.set_font()

        main_layout = QHBoxLayout(self)

        self.submit_button = QPushButton("Submit")
        self.route_view = DownWidget()
        left_layout = self.add_left_area()
        right_layout = self.add_stock_view()

        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 2)

        self.setWindowTitle("Island Trade")
        self.resize(1700, 900)

        self.submit_button.clicked.connect(self.run_schedule)

        self.submit_button_signal.connect(self.route_view.update_routes)

    def add_left_area(self):
        left_layout = QVBoxLayout(self)
        self.setLayout(left_layout)

        left_layout.addWidget(TopWidget(), 1)
        left_layout.addWidget(MiddleWidget(self.islands), 2)

        left_layout.addWidget(self.submit_button)

        left_layout.addWidget(self.route_view, 2)
        return left_layout

    def add_stock_view(self):
        right_layout = QVBoxLayout(self)
        right_layout.addWidget(StockWidget())
        return right_layout

    def set_font(self):
        font = QFont("Microsoft JhengHei", 12)
        QApplication.setFont(font)

    def run_schedule(self):
        print('run_schedule')
        exchanges = {}
        for group in self.item_groups:
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
