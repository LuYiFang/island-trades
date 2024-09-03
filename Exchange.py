import logging
import math
import os
import re
from collections import defaultdict
from datetime import datetime

from Island import IslandGraph
from Stock import Stock
from exchange_items import default_ship_load_capacity
from utility import Save, Exchange


class ExchangeGraph(Save):
    def __init__(self, stock: Stock, island_graph: IslandGraph):
        super().__init__()

        self.graph = {}
        self.save_graph = {}
        self.ship_load_capacity = default_ship_load_capacity
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

            if current_weight > self.ship_load_capacity - 100 or current_swap_cost <= 0:
                return current_priority, visited, island_trades, current_swap_cost

            if len(self.graph) == len(visited):
                return current_priority, visited, island_trades, current_swap_cost

            max_value = -float('inf')
            best_route = set()
            best_island_trades = {}
            best_remain_swap_cost = 0
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

                if current_weight + (
                        max_allowable_trades * exchange.ratio * exchange.weight) > self.ship_load_capacity:
                    continue

                all_exchange_zero = False
                new_state = (
                    exchange.island,
                    current_weight + (max_allowable_trades * exchange.ratio * exchange.weight),
                    current_swap_cost - (max_allowable_trades * exchange.swap_cost),
                    exchange.priority + current_priority,
                )
                island_trades[exchange.island] = max_allowable_trades
                value, route, route_trades, remain_swap_cost = dp(new_state, visited | {exchange.island},
                                                                  island_trades.copy())

                if value > max_value:
                    max_value = value
                    best_route = route
                    best_island_trades = route_trades
                    best_remain_swap_cost = remain_swap_cost

            if all_exchange_zero:
                return current_priority, visited, island_trades, current_swap_cost

            return max_value, best_route, best_island_trades, best_remain_swap_cost

        total_swap_cost = 1000000
        min_swap_cost = 11280
        best_routes = []

        def find_best_routes(island, swap_cost):
            if swap_cost < min_swap_cost:
                return
            _, route, island_trades, remain_swap_cost = dp((
                island,
                0,
                swap_cost,
                self.graph[island].priority,
            ),
                set(),
                {}
            )

            if not route:
                print('no route', island, self.graph[island].remain_exchange, swap_cost)
                return

            route_exchanges = {}
            for _island in sorted(route, key=lambda x: self.island_graph.calculate_distance_with_start_island(x)):
                trades = island_trades[_island]
                _exchange = self.graph[_island]
                self.stock.execute_exchange(_exchange, trades)
                _exchange.remain_exchange -= trades

                route_exchanges[_island] = (_exchange, trades)
            best_routes.append(route_exchanges)

            tradable_islands = list(filter(lambda x: x[1].remain_exchange > 0, self.graph.items()))
            if len(tradable_islands) <= 0:
                return

            find_best_routes(tradable_islands[0][0], remain_swap_cost)
            return

        first_island = list(self.graph.keys())[0]
        find_best_routes(first_island, total_swap_cost)

        print('best_routes')
        for _route in best_routes:
            print()
            for i, v in _route.items():
                print(i, v[1], v[0].swap_cost, end=' ')
        print('best_routes end', type(best_routes))
        return best_routes
