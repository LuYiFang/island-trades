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
    def __init__(self, ship_load_capacity, stock: Stock, island_graph: IslandGraph):
        super().__init__()

        self.graph = {}
        self.save_graph = {}
        self.ship_load_capacity = ship_load_capacity
        self.stock = stock
        self.island_graph = island_graph
        self.start_island = island_graph.start_island

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
        self.count_priority()

    @staticmethod
    def scale_to_range(value, original_min, original_max, new_min=1, new_max=10):
        if original_min == original_max:
            return new_min
        return new_min + (value - original_min) / (original_max - original_min) * (new_max - new_min)

    def count_priority(self):
        for island, exchange in self.graph.items():
            stock_min = min(self.stock.stock.values())
            stock_max = max(self.stock.stock.values())

            exchange.priority += self.scale_to_range(- self.stock[exchange.target], -stock_min, -stock_max)
            exchange.priority += self.scale_to_range(exchange.price, 2000000, 7500000)

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

            self.save_json(filename.format(version + 1), target)

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

        #  優先條件: 要囤貨 > 數量較少 > 高價值

        def dp(state, visited, island_trades):
            current_island, current_weight, current_swap_cost, current_priority = state

            if current_weight > self.ship_load_capacity or current_swap_cost <= 0:
                return current_priority, visited, island_trades

            if len(self.graph) == len(visited):
                return current_priority, visited, island_trades

            max_value = -float('inf')
            best_route = set()
            best_island_trades = {}
            all_exchange_zero = True

            for exchange in self.graph.values():
                if exchange.island in visited:
                    continue

                if not self.island_graph.is_island_valid(exchange.island, visited):
                    continue

                max_allowable_trades = exchange.count_max_allowable_trades(self.ship_load_capacity - current_weight,
                                                                           self.stock[exchange.source],
                                                                           current_swap_cost)

                if max_allowable_trades <= 0:
                    continue

                if current_weight + (max_allowable_trades * exchange.ratio * exchange.weight) > self.ship_load_capacity:
                    continue

                all_exchange_zero = False
                new_state = (
                    exchange.island,
                    current_weight + (max_allowable_trades * exchange.ratio * exchange.weight),
                    current_swap_cost - max_allowable_trades * exchange.swap_cost,
                    exchange.priority + current_priority,
                )
                island_trades[exchange.island] = max_allowable_trades
                value, route, route_trades = dp(new_state, visited | {exchange.island}, island_trades.copy())

                if value > max_value:
                    max_value = value
                    best_route = route
                    best_island_trades = route_trades

            if all_exchange_zero:
                return current_priority, visited, island_trades

            return max_value, best_route, best_island_trades

        first_island = list(self.graph.keys())[0]
        v, r, t = dp((
            first_island,
            0,
            1000000,
            self.graph[first_island].priority,
        ),
            set(),
            {}
        )

        graph_filter = filter(lambda x: x[1].ratio != 0, self.graph.items())
        sorted_graph = dict(
            sorted(graph_filter, key=lambda x: (x[1].priority, self.get_exchange_weight(x[1])), reverse=True))
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

        find_routes(0, sorted_graph)
        return routes
