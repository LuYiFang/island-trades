import logging
import os
import re
from datetime import datetime

from Island import IslandGraph
from Stock import Stock
from exchange_items import default_ship_load_capacity, default_swap_cost
from utility import Save, Exchange, Station_tuple, Route_tuple


class Scheduler(Save):
    def __init__(self, stock: Stock, island_graph: IslandGraph):
        super().__init__()

        self.read_settings()

        self.exchanges = {}
        self.save_exchanges = {}

        if not self.__dict__.get('ship_load_capacity'):
            self.ship_load_capacity = default_ship_load_capacity
        self.stock = stock
        self.island_graph = island_graph
        self.start_island = island_graph.start_island
        self.min_swap_cost = None
        self.total_swap_cost = 1000000

        if not self.__dict__.get('default_swap_cost'):
            self.default_swap_cost = default_swap_cost

        self.checked_stations = {}
        self.settings = {}

    def read_settings(self):
        settings = self.__dict__.get('settings')
        if not settings:
            return

        self.ship_load_capacity = settings.get('ship_load_capacity', default_ship_load_capacity)
        self.default_swap_cost = settings.get('default_swap_cost', default_swap_cost)

    def add_trade(self, exchanges: dict):
        self.save_exchanges = {}
        self.exchanges = {}
        for island, args in exchanges.items():
            level = self.stock.item_level.get(args[1])
            weight = self.stock.item_weight.get(args[1])
            source_img = self.stock.item_info.get(args[0], {}).get('img', '')
            target_img = self.stock.item_info.get(args[1], {}).get('img', '')
            self.exchanges[island] = Exchange(
                island, *args,
                level, weight,
                source_img=source_img, target_img=target_img)
            self.save_exchanges[island] = {
                'source': args[0],
                'target': args[1],
                'ratio': args[2],
                'swap_cost': args[3],
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
            exchange.priority += self.scale_to_range(
                self.stock.reserved_quantity[exchange.target],
                0, max(self.stock.reserved_quantity.values())
            )
            if exchange.level == 'material':
                exchange.priority += 10

    def count_version(self, filename):
        version = 1
        for f in os.listdir(self.folder):
            f.startswith(filename)
            match = re.search(r'_v(\d+)', f)
            if not match:
                continue

            _version = int(match.group(1))
            if _version > version:
                version = _version
        return version

    def save_exchanges_all(self, *args):
        for target_name in args:
            target = self.__dict__.get(target_name)
            if not target:
                continue

            date = datetime.today().strftime('%Y%m%d')
            filename = f'{target_name}_{date}_v{{}}'
            version = self.count_version(filename)

            self.save_json(filename.format(version + 1), target)

    def save_exchanges_remain(self):
        exchanges_remain = {}

        remain_swap_cost = self.total_swap_cost
        for island, exchange in self.exchanges.items():
            checked_station = self.checked_stations.get(island)
            remain_trades = exchange.remain_exchange
            if checked_station:
                remain_swap_cost -= checked_station.trades * exchange.swap_cost
                remain_trades -= checked_station.trades

            if remain_trades <= 0:
                continue

            exchanges_remain[island] = {
                'source': exchange.source,
                'target': exchange.target,
                'ratio': exchange.ratio,
                'swap_cost': exchange.swap_cost,
                'remain_trades': remain_trades,
            }

        exchanges_remain['remain_swap_cost'] = remain_swap_cost

        date = datetime.today().strftime('%Y%m%d')
        filename = f'remain_exchanges_{date}_v{{}}'
        version = self.count_version(filename)

        self.save_json(filename.format(version + 1), exchanges_remain)

    def save_settings(self):
        self.settings = {
            'ship_load_capacity': self.ship_load_capacity,
            'default_swap_cost': self.default_swap_cost,
        }
        self.save('settings')

    def execute_exchange(self, exchange: Exchange, trades, route_id):
        self.stock.execute_exchange(exchange, trades, route_id)

        new_trades = trades
        if self.checked_stations.get(exchange.island):
            new_trades += self.checked_stations[exchange.island].trades
        self.checked_stations[exchange.island] = Station_tuple(exchange, new_trades)

    def undo_execute_exchange(self, exchange: Exchange, trades, route_id):
        self.stock.undo_execute_exchange(exchange, trades, route_id)

        if not self.checked_stations.get(exchange.island):
            return

        new_trades = self.checked_stations[exchange.island].trades - trades
        if new_trades <= 0:
            del self.checked_stations[exchange.island]
            return
        self.checked_stations[exchange.island] = Station_tuple(exchange, new_trades)

    def get_swap_cost(self):
        return min(self.exchanges.values(), key=lambda x: x.swap_cost).swap_cost

    def reset_all_exchanges(self):
        for exchange in self.exchanges.values():
            exchange.reset_remain_exchange()
        self.checked_stations = {}

    def schedule_routes(self):
        self.stock.restore()
        self.stock.switch_stock(True)
        self.reset_all_exchanges()

        remain_swap_cost = self.total_swap_cost

        best_routes = []
        try:
            # 伊利亞
            start_island_exchange = self.exchanges.get(self.start_island)
            if start_island_exchange:
                available_stock = self.stock.count_available_stock(start_island_exchange)
                if available_stock > 0:
                    max_trades = start_island_exchange.count_max_allowable_trades(
                        100000000,
                        available_stock,
                        remain_swap_cost
                    )
                    route_exchanges = self.virtual_execute_exchange({self.start_island}, {self.start_island: max_trades})
                    best_routes.append(Route_tuple(f'{self.start_island}', route_exchanges))

            # 伊利亞 - 貝村
            route_exchanges, remain_swap_cost = self.find_specify_route(self.start_island, '貝村',
                                                                        remain_swap_cost)
            if route_exchanges:
                best_routes.append(Route_tuple(f'{self.start_island} - 貝村', route_exchanges))

            # 伊利亞 - 澳眼
            route_exchanges, remain_swap_cost = self.find_specify_route(self.start_island, '澳眼',
                                                                        remain_swap_cost)
            if route_exchanges:
                best_routes.append(Route_tuple(f'{self.start_island} - 澳眼', route_exchanges))

            first_island = list(self.exchanges.keys())[0]
            routes = self.find_best_routes(0, first_island, remain_swap_cost)
            best_routes.extend(routes)

            self.reset_all_exchanges()
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
        return self.virtual_execute_exchange(route_1, island_trades_1), remain_swap_cost

    def find_best_routes(self, index, island, swap_cost):
        if swap_cost < self.min_swap_cost:
            return []

        pr, route, island_trades, remain_swap_cost = self.route_dp((
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

        route_exchanges = self.virtual_execute_exchange(route, island_trades)
        index += 1

        group = [Route_tuple(f'Group {index}', route_exchanges)]

        tradable_islands = list(filter(lambda x: x[1].remain_exchange > 0, self.exchanges.items()))
        if len(tradable_islands) <= 0:
            return group

        next_route = self.find_best_routes(index, tradable_islands[0][0], remain_swap_cost)

        return group + next_route

    def route_dp(self, state, visited, island_trades, exchanges):
        current_island, current_weight, current_swap_cost, current_priority = state

        if current_weight > self.ship_load_capacity - 100 or current_swap_cost <= self.min_swap_cost:
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

            available_stock = self.stock.count_available_stock(exchange)
            max_allowable_trades = exchange.count_max_allowable_trades(
                self.ship_load_capacity - current_weight,
                available_stock,
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

    def virtual_execute_exchange(self, route, island_trades):
        route_exchanges = []
        for island in self.island_graph.find_best_path(list(route)):
            trades = island_trades[island]
            exchange = self.exchanges[island]
            self.stock.execute_exchange(exchange, trades)
            exchange.remain_exchange -= trades

            route_exchanges.append(Station_tuple(exchange, trades))
        return route_exchanges
