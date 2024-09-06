import json
import math
import os
from collections import namedtuple

Station_tuple = namedtuple('Station_tuple', ['exchange', 'trades'])
Route_tuple = namedtuple('Route_tuple', ['name', 'stations'])


def read_json(filename):
    with open(filename, 'r') as f:
        return json.load(f)


class Save:
    def __init__(self):
        self.folder = 'storage'
        os.makedirs(self.folder, exist_ok=True)

        storage_object = self.read()
        self.__dict__.update(storage_object)

    def save_json(self, filename, data):
        with open(f'{self.folder}/{filename}.json', 'w') as f:
            json.dump(data, f)

    def read_json(self, filename):
        return read_json(f'{self.folder}/{filename}')

    def save(self, *args):
        for target_name in args:
            target = self.__dict__.get(target_name)
            if not target:
                continue

            self.save_json(f'{self.__class__.__name__}_{target_name}', target)

    def read(self):
        prefix = f'{self.__class__.__name__}'
        files = [f for f in os.listdir(self.folder) if f.startswith(prefix) and f.endswith('.json')]

        storage_object = {}
        for filename in files:
            data = self.read_json(filename)
            target_name = filename.replace(f'{prefix}_', '').replace('.json', '')
            storage_object[target_name] = data
        return storage_object


class Exchange:
    def __init__(
            self,
            island, source, target, ratio,
            swap_cost=11485, level=None, weight=0, priority=1,
            source_img='', target_img='',
    ):
        self.island = island
        self.source = source
        self.target = target
        self.ratio = ratio
        self.swap_cost = swap_cost
        self.weight = weight
        self.priority = priority
        self.source_img = source_img
        self.target_img = target_img

        self.maximum_exchange = 10
        self.level = level

        if self.level == 5:
            self.maximum_exchange = 6

        self.trades = 1000
        self.remain_exchange = self.maximum_exchange

        self.price = self.get_price()

    def get_price(self):
        if self.level == 5:
            return 7500000
        if self.level == 4:
            return 5000000
        if self.level == 3:
            return 4000000
        if self.level == 2:
            return 3000000
        if self.level == 1:
            return 2000000
        return 0

    def count_max_allowable_trades(self, load_capacity, available_stock, current_swap_cost):
        if self.level == 1:
            available_stock = 1000

        if self.ratio == 0:
            max_trades = 0
        else:
            max_trades = math.floor(math.floor(load_capacity / self.weight) / self.ratio)
        max_swap_cost = math.floor(current_swap_cost / self.swap_cost)
        return min(
            self.maximum_exchange,
            self.remain_exchange,
            max_trades,
            available_stock,
            max_swap_cost,
        )
