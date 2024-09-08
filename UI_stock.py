import logging

from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QPushButton, QGroupBox, QGridLayout, QLabel, QSpinBox, QVBoxLayout, QHBoxLayout

from UI_widget import ScrollableWidget


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

                quantity_count = self.stock.reserved_quantity.get(item['name'], 0)
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

                row = item_index // 3
                col = item_index % 3

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
