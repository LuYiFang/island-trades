import functools
import json
import logging
import os


def exception_handler(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            print('args', args)
            print('kwargs', kwargs)
            # args.pop()
            return func(*args[1:], **kwargs)
        except Exception as e:
            logging.exception(e)
    return wrapper


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
        with open(f'{self.folder}/{filename}', 'r') as f:
            return json.load(f)

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
    def __init__(self, island, source, target, ratio, swap_cost=11485, trades=None, level=None, weight=0, priority=1):
        self.island = island
        self.source = source
        self.target = target
        self.ratio = ratio
        self.swap_cost = swap_cost
        self.weight = weight
        self.priority = priority

        self.maximum_exchange = 10
        self.level = level

        if self.level == 5:
            self.maximum_exchange = 6

        self.trades = trades if trades else self.maximum_exchange
        self.remain_exchange = self.init_remain_exchange()

    def init_remain_exchange(self):
        if self.trades > self.maximum_exchange:
            return self.maximum_exchange
        return self.trades
