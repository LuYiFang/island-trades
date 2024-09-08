import logging
from collections import defaultdict

from exchange_items import trade_items
from utility import Save, Exchange


class Stock(Save):
    def __init__(self):
        super().__init__()

        self.ori_stock = {}
        self._calc_stock = {}
        self.reserved_quantity = {}

        if not self.__dict__.get('trade_items'):
            self.trade_items = trade_items
        else:
            int_trade_items = {}
            for level, items in self.trade_items.items():
                try:
                    level = int(level)
                except:
                    pass

                int_trade_items[level] = items
            self.trade_items = int_trade_items

        if not self.__dict__.get('_stock'):
            self._stock = {}

        self.item_images = {}
        self.set_stock_default()
        self.stock = self._calc_stock

        self.item_level = self.update_item_level()
        self.item_weight = self.update_item_weight()

        self.auto_sell = True
        self.sell_quantity = defaultdict(int)

    def __getitem__(self, item):
        return self.stock.get(item, 0)

    def __setitem__(self, key, value):
        self.stock[key] = value

    def switch_stock(self, is_calc=False):
        self.stock = self._calc_stock if is_calc else self._stock

    def set_stock_default(self):
        all_items = []

        for items in self.trade_items.values():
            for item in items:
                all_items.append(item['name'])
                self.item_images[item['name']] = item.get('img', '')

        if not self.__dict__.get('_stock'):
            self._stock = {}

        unset_items = set(all_items) - set(self._stock.keys())
        self._stock.update({item: 0 for item in unset_items})
        self._calc_stock = self._stock.copy()
        self.ori_stock = self._stock.copy()

        if not self.__dict__.get('reserved_quantity'):
            self.reserved_quantity = {item: 0 for item in all_items}
            for item in self.trade_items[5]:
                self.reserved_quantity[item['name']] = 2

    def execute_exchange(self, exchange: Exchange, trades, route_id=None):
        if exchange.level != 1:
            self.stock[exchange.source] -= trades

        self.stock[exchange.target] += trades * exchange.ratio

        if exchange.level == 5 and self.auto_sell and route_id is not None:
            reserved_count = self.reserved_quantity.get(exchange.target, 0)
            self.sell_quantity[route_id] += self.stock[exchange.target] - reserved_count
            self.stock[exchange.target] = reserved_count

    def undo_execute_exchange(self, exchange: Exchange, trades, route_id=None):
        if exchange.level != 1:
            self.stock[exchange.source] += trades
        self.stock[exchange.target] -= trades * exchange.ratio

        if exchange.level == 5 and self.auto_sell and route_id is not None:
            self.stock[exchange.target] += self.sell_quantity[route_id]
            self.sell_quantity[route_id] = 0

    def restore(self):
        self._stock = self.ori_stock.copy()
        self._calc_stock = self.ori_stock.copy()

    def update_trade_items(self, level, item):
        self.trade_items[level].append({'name': item})
        self.item_level = self.update_item_level()
        self.item_weight = self.update_item_weight()

        self.set_stock_default()

    def update_item_level(self):
        item_level = {}
        for level, items in self.trade_items.items():
            for item in items:
                item_level[item['name']] = level
        return item_level

    def update_item_weight(self):
        item_weight = {}
        for level, items in self.trade_items.items():
            for item in items:
                weight = 1
                if level == 1:
                    weight = 100
                elif level == 2:
                    weight = 800
                elif level == 3:
                    weight = 900
                elif level == 4 or level == 5:
                    weight = 1000
                item_weight[item['name']] = weight
        return item_weight

    def switch_auto_sell(self, auto_sell):
        self.auto_sell = auto_sell

    def count_income(self):
        return sum(self.sell_quantity.values()) * 7500000

    def count_available_stock(self, exchange: Exchange):
        if exchange.level == 'material':
            return self.stock[exchange.source]
        return self.stock[exchange.source] - self.reserved_quantity.get(exchange.source, 0)

    def save(self):
        super().save(
            'trade_items',
            '_stock',
            'reserved_quantity',
        )
