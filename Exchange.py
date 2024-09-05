import logging
import os
import re
from datetime import datetime

from Island import IslandGraph
from Stock import Stock
from exchange_items import default_ship_load_capacity
from utility import Save, Exchange, Station_tuple, Route_tuple


class Scheduler(Save):
    def __init__(self, stock: Stock, island_graph: IslandGraph):
        super().__init__()

        self.exchanges = {}
        self.save_exchanges = {}
        self.ship_load_capacity = default_ship_load_capacity
        self.stock = stock
        self.island_graph = island_graph
        self.start_island = island_graph.start_island
        self.min_swap_cost = None
        self.total_swap_cost = 1000000

    def add_trade(self, exchanges: dict):
        self.save_exchanges = {}
        self.exchanges = {}
        for island, args in exchanges.items():
            level = self.stock.item_level.get(args[1])
            weight = self.stock.item_weight.get(args[1])
            source_img = self.stock.item_images.get(args[0], '')
            target_img = self.stock.item_images.get(args[1], '')
            self.exchanges[island] = Exchange(
                island, *args,
                level, weight,
                source_img=source_img, target_img=target_img)
            self.save_exchanges[island] = {
                'source': args[0],
                'target': args[1],
                'ratio': args[2],
            }
        self.count_priority()
        self.min_swap_cost = self.get_swap_cost()

    @staticmethod
    def scale_to_range(value, original_min, original_max, new_min=1, new_max=10):
        if original_min == original_max:
            return new_min
        return new_min + (value - original_min) / (original_max - original_min) * (new_max - new_min)

    def count_priority(self):
        for island, exchange in self.exchanges.items():
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

    def get_swap_cost(self):
        return min(self.exchanges.values(), key=lambda x: x.swap_cost).swap_cost

    def schedule_routes(self):
        self.stock.restore()
        self.stock.switch_stock(True)

        best_routes = []
        try:
            start_island_exchange = self.exchanges.get(self.start_island)
            if start_island_exchange:
                max_trades = start_island_exchange.count_max_allowable_trades(
                    self.ship_load_capacity,
                    self.stock[start_island_exchange.source],
                    self.stock.reserved_quantity[start_island_exchange.source],
                    self.total_swap_cost
                )
                route_exchanges = self.execute_exchange({self.start_island}, {self.start_island: max_trades})
                best_routes.append(Route_tuple(f'{self.start_island}', route_exchanges))

            route_exchanges, remain_swap_cost = self.find_specify_route(self.start_island, '貝村',
                                                                        self.total_swap_cost)
            if route_exchanges:
                best_routes.append(Route_tuple(f'{self.start_island} - 貝村', route_exchanges))
            route_exchanges, remain_swap_cost = self.find_specify_route(self.start_island, '庭貝拉',
                                                                        remain_swap_cost)
            if route_exchanges:
                best_routes.append(Route_tuple(f'{self.start_island} - 庭貝拉', route_exchanges))
            route_exchanges, remain_swap_cost = self.find_specify_route(self.start_island, '澳眼',
                                                                        remain_swap_cost)
            if route_exchanges:
                best_routes.append(Route_tuple(f'澳眼 - {self.start_island}', route_exchanges))

            first_island = list(self.exchanges.keys())[0]
            routes = self.find_best_routes(0, first_island, remain_swap_cost)
            best_routes.extend(routes)

            print('best_routes')
            for _route in best_routes:
                print('\ngroup', _route.name)
                for r in _route.stations:
                    print(r.exchange.island, r.trades, end=' ')
            print('\nbest_routes end', type(best_routes))
        except Exception as e:
            logging.exception(e)
        return best_routes

    def find_specify_route(self, start_island, end_island, remain_swap_cost):
        target_islands = self.island_graph.find_passed_islands(start_island, end_island)
        target_islands.extend(self.island_graph.find_nearby_islands(start_island, 7))
        target_exchanges = {island: self.exchanges[island] for island in target_islands if
                            self.exchanges.get(island)}
        _, route_1, island_trades_1, remain_swap_cost = self.route_dp(
            (self.island_graph.start_island, 0, remain_swap_cost, 0),
            set(),
            {},
            target_exchanges
        )
        return self.execute_exchange(route_1, island_trades_1), remain_swap_cost

    def find_best_routes(self, index, island, swap_cost):
        if swap_cost < self.min_swap_cost:
            return []

        _, route, island_trades, remain_swap_cost = self.route_dp((
            island,
            0,
            swap_cost,
            self.exchanges[island].priority,
        ),
            set(),
            {},
            self.exchanges
        )

        # 避免 maximum recursion depth exceeded
        if not route:
            print('no route', island, self.exchanges[island].remain_exchange, swap_cost)
            return []

        route_exchanges = self.execute_exchange(route, island_trades)
        index += 1

        group = [Route_tuple(f'Group {index}', route_exchanges)]

        tradable_islands = list(filter(lambda x: x[1].remain_exchange > 0, self.exchanges.items()))
        if len(tradable_islands) <= 0:
            return group

        next_route = self.find_best_routes(index, tradable_islands[0][0], remain_swap_cost)

        return group + next_route

    def route_dp(self, state, visited, island_trades, exchanges):
        current_island, current_weight, current_swap_cost, current_priority = state

        if current_weight > self.ship_load_capacity - 100 or current_swap_cost <= 0:
            return current_priority, visited, island_trades, current_swap_cost

        if len(exchanges) == len(visited):
            return current_priority, visited, island_trades, current_swap_cost

        max_value = -float('inf')
        best_route = set()
        best_island_trades = {}
        best_remain_swap_cost = 0
        all_exchange_zero = True

        for exchange in exchanges.values():
            if exchange.island in visited:
                continue

            if not self.island_graph.is_island_valid(exchange.island, visited):
                continue

            max_allowable_trades = exchange.count_max_allowable_trades(
                self.ship_load_capacity - current_weight,
                self.stock[exchange.source],
                self.stock.reserved_quantity[exchange.source],
                current_swap_cost
            )

            if max_allowable_trades <= 0:
                continue

            if current_weight + (max_allowable_trades * exchange.ratio * exchange.weight) \
                    > self.ship_load_capacity:
                continue

            all_exchange_zero = False
            new_state = (
                exchange.island,
                current_weight + (max_allowable_trades * exchange.ratio * exchange.weight),
                current_swap_cost - (max_allowable_trades * exchange.swap_cost),
                exchange.priority + current_priority,
            )
            island_trades[exchange.island] = max_allowable_trades
            value, route, route_trades, remain_swap_cost = self.route_dp(
                new_state, visited | {exchange.island},
                island_trades.copy(),
                exchanges
            )

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
    def execute_exchange(self, route, island_trades):
        route_exchanges = []
        for island in sorted(route, key=lambda x: self.island_graph.calculate_distance_with_start_island(x)):
            print('island', island)
            trades = island_trades[island]
            exchange = self.exchanges[island]
            self.stock.execute_exchange(exchange, trades)
            exchange.remain_exchange -= trades

            route_exchanges.append(Station_tuple(exchange, trades))
        return route_exchanges
