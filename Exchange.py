import logging
import math
import os
import re
from collections import defaultdict
from datetime import datetime

from Island import IslandGraph
from Stock import Stock
from utility import Save, Exchange


class ExchangeGraph(Save):
    def __init__(self, start_island, ship_load_capacity, stock: Stock, island_graph: IslandGraph):
        super().__init__()

        self.graph = {}
        self.ship_load_capacity = ship_load_capacity
        self.stock = stock
        self.island_graph = island_graph
        self.start_island = start_island

    def add_trade(self, exchanges: dict):
        self.save_graph = {}
        self.graph = {}
        for island, args in exchanges.items():
            level = self.stock.item_level.get(args[1])
            weight = self.stock.item_weight.get(args[1])
            self.graph[island] = Exchange(island, *args, level, weight)
            self.save_graph[island] = {
                'source': args[0],
                'target': args[1],
                'ratio': args[2],
            }
        self.save('save_graph')

    def save(self, *args):

        for target_name in args:
            target = self.__dict__.get(target_name)
            if not target:
                continue

            date = datetime.today().strftime('%Y%m%d')
            filename = f'{self.__class__.__name__}_{target_name}_{date}_v{{}}'
            version = 1
            for f in os.listdir(self.folder):
                f.startswith(filename)
                match = re.search(r'_v(\d+)', f)
                if not match:
                    continue

                _version = int(match.group(1))
                if _version > version:
                    version = _version

            self.save_json(filename.format(version), target)

    def count_max_allowable_exchange(self, exchange: Exchange):
        if exchange.level == 1:
            return 10

        max_exchange = math.floor(math.floor(self.ship_load_capacity / exchange.weight) / exchange.ratio)
        return min(exchange.trades, exchange.maximum_exchange, max_exchange, self.stock[exchange.source],
                   exchange.remain_exchange)

    def count_max_allowable_weight(self, exchange: Exchange):
        return self.count_max_allowable_exchange(exchange) * exchange.ratio * exchange.weight

    def count_remaining_weight(self, exchange: Exchange):
        return self.ship_load_capacity - self.count_max_allowable_weight(exchange)

    def count_min_weight(self, exchange: Exchange):
        return exchange.weight * exchange.ratio

    def find_available_exchange(self, target):
        # 從附近 or 會路過的島找
        self.island_graph.nearby_islands(target, 2)

    def find_unfulfilled_exchange(self):
        sorted_graph = dict(sorted(self.graph.items(), key=lambda x: x[1].level))

        unfulfilled = {}
        target_numbers = {}
        for island, exchange in sorted_graph.items():
            if exchange.level == 1:
                target_numbers[exchange.target] = 10
                continue

            max_allowable_trades = self.count_max_allowable_exchange(exchange)
            target_numbers[exchange.target] = max_allowable_trades * exchange.ratio + self.stock[exchange.target]

            if self.stock[exchange.source] >= max_allowable_trades:
                continue

            if target_numbers.get(exchange.source, 0) >= max_allowable_trades:
                continue

            unfulfilled[island] = exchange
        return unfulfilled

    def pick_island(self, overlap):
        selections = []

        sorted_overlap = dict(sorted(overlap.items(), key=lambda x: len(x[1])))

        def pick(index):
            first_keys = list(sorted_overlap.keys())
            if len(first_keys) <= 0:
                return {}
            first_key = first_keys[0]
            first_list = sorted_overlap[first_key]
            if index >= len(first_list):
                return {}

            first_island = first_list[index]
            target_overlap = sorted_overlap.copy()
            target_overlap.pop(first_key)
            selections.append(first_island)

            for island, island_list in target_overlap.items():
                for i, nearby_island in enumerate(island_list):
                    if nearby_island in selections:
                        continue
                    selections.append(nearby_island)
                    break

        max_count = 50
        index = 0
        pick(index)
        while len(selections) != len(overlap) and index < max_count:
            selections = []
            index += 1
            pick(index)

        return {selections[i]: k for i, k in enumerate(sorted_overlap.keys())}

    def get_exchange_weight(self, exchange: Exchange, trades=None):
        if exchange.level == 1:
            return 1000

        available_exchange = exchange.maximum_exchange if trades is None else trades
        if available_exchange > self.stock[exchange.source]:
            available_exchange = self.stock[exchange.source]
        return available_exchange * exchange.ratio * exchange.weight

    def schedule_routes(self):
        self.stock.restore()
        self.stock.switch_stock(True)

        graph_filter = filter(lambda x: x[1].ratio != 0, self.graph.items())
        sorted_graph = dict(sorted(graph_filter, key=lambda x: self.get_exchange_weight(x[1]), reverse=True))
        routes = defaultdict(dict)

        def find_routes(index, graph):
            if not graph:
                return

            current_island = next(iter(graph))
            current_exchange = graph[current_island]

            remain_weight = self.ship_load_capacity

            max_allowable_exchange = self.count_max_allowable_exchange(current_exchange)

            if max_allowable_exchange <= 0:
                return

            if len(graph) <= 1:
                routes[f'group_{index}'].update({
                    current_island: {
                        'source': current_exchange.source,
                        'exchange': max_allowable_exchange,
                        'target': current_exchange.target,
                        'exchange_obj': current_exchange,
                    }
                })
                return

            self.stock.execute_exchange(current_exchange, max_allowable_exchange)
            current_exchange.remain_exchange -= max_allowable_exchange
            remain_weight -= max_allowable_exchange * current_exchange.ratio * current_exchange.weight

            routes[f'group_{index}'].update({
                current_island: {
                    'source': current_exchange.source,
                    'exchange': max_allowable_exchange,
                    'target': current_exchange.target,
                    'exchange_obj': current_exchange,
                }
            })

            graph.pop(current_island)
            if current_exchange.remain_exchange > 0:
                graph[current_island] = current_exchange

            if remain_weight <= 100:  # 負重最小值
                find_routes(index + 1, graph)
                return

            nearby_islands = self.island_graph.nearby_islands(current_island, 2)
            nearby_islands = set(graph.keys()).intersection(nearby_islands)
            passed_islands = self.island_graph.find_passed_islands(self.start_island, current_island)
            passed_islands = set(graph.keys()).intersection(passed_islands)
            merge_islands = {*nearby_islands, *passed_islands}

            merge_exchanges = {}
            for merge_island in merge_islands:
                if self.count_min_weight(graph[merge_island]) > remain_weight:
                    continue
                merge_exchanges[merge_island] = graph[merge_island]

            merge_exchanges = dict(
                sorted(merge_exchanges.items(), key=lambda x: self.count_min_weight(x[1]), reverse=True))

            for merge_island, merge_exchange in merge_exchanges.items():
                available_merge_trades = math.floor(
                    math.floor(remain_weight / self.count_min_weight(merge_exchange)) / merge_exchange.ratio)

                available_merge_trades = min(
                    merge_exchange.trades,
                    merge_exchange.maximum_exchange,
                    available_merge_trades,
                    self.stock[merge_exchange.source],
                    merge_exchange.remain_exchange
                )

                if available_merge_trades <= 0:
                    continue

                self.stock.execute_exchange(merge_exchange, available_merge_trades)
                remain_weight -= available_merge_trades * merge_exchange.ratio * merge_exchange.weight
                merge_exchange.remain_exchange -= available_merge_trades

                graph.pop(merge_island)
                if merge_exchange.remain_exchange > 0:
                    graph[merge_island] = merge_exchange

                routes[f'group_{index}'].update({
                    merge_island: {
                        'source': merge_exchange.source,
                        'exchange': available_merge_trades,
                        'target': merge_exchange.target,
                        'exchange_obj': merge_exchange,
                    }
                })

                if remain_weight <= 0:
                    break

            find_routes(index + 1, graph)

        try:
            find_routes(0, sorted_graph)
        except Exception as e:
            logging.exception(e)

        return routes

    def tune(self):
        pass
