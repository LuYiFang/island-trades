import heapq
import math
import os
import pickle
from collections import defaultdict
from pprint import pprint
from typing import TypeVar, Optional

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

from exchange_items import level_1_items, level_2_items, level_3_items, level_4_items, level_5_items

T = TypeVar('T', bound='Save')


class Save:
    def __init__(self):
        pass

    def save(self):
        with open(f'{self.__class__.__name__}.pkl', 'wb') as f:
            pickle.dump(self, f)

    @classmethod
    def read(cls) -> Optional[T]:
        filename = f'{cls.__name__}.pkl'
        if not os.path.exists(filename):
            return
        with open(filename, 'rb') as f:
            return pickle.load(f)


class IslandGraph(Save):
    def __init__(self):
        super().__init__()
        self.graph = {}
        self.group_graph = {}
        self.island_group_map = {}
        self.group_island_map = defaultdict(list)

    def add_edge(self, u, v, weight, group=False):
        graph = self.group_graph if group else self.graph

        if u not in graph:
            graph[u] = []
        graph[u].append((v, weight))

        if v not in graph:
            graph[v] = []
        graph[v].append((u, weight))

    def nearby_islands(self, island, max_distance):
        nearby = []
        for neighbor, weight in self.graph[island]:
            if weight <= max_distance:
                nearby.append(neighbor)
        return nearby

    def cluster_islands(self, num_clusters):
        islands = sorted(list(self.graph.keys()))
        n = len(islands)
        distance_matrix = np.full((n, n), 100)

        for index in range(len(islands)):
            distance_matrix[index][index] = 0

        for u_index, u in enumerate(islands):
            for v, weight in self.graph[u]:
                v_index = islands.index(v)
                distance_matrix[u_index][v_index] = weight

        # print(pd.DataFrame(distance_matrix,  index=islands, columns=islands))

        k_means = KMeans(n_clusters=num_clusters).fit(distance_matrix)

        group = defaultdict(list)
        for i, label in enumerate(k_means.labels_):
            group[f'group_{label}'].append(islands[i])
            self.island_group_map[islands[i]] = f'group_{label}'
        self.group_island_map = group

        self.create_group_graph(group, islands, distance_matrix)
        pprint(group)
        return group

    def create_group_graph(self, group, islands, distance_matrix):
        island_map = {island: i for i, island in enumerate(islands)}

        def get_edge_weight(u, v):
            u_index = island_map[u]
            v_index = island_map[v]
            return distance_matrix[u_index][v_index]

        counted_group_pair = []
        for group_name_i, island_list_i in group.items():
            for group_name_j, island_list_j in group.items():
                if group_name_i == group_name_j:
                    continue

                pair_set = {group_name_i, group_name_j}
                if pair_set in counted_group_pair:
                    continue

                counted_group_pair.append(pair_set)

                min_distance = float('inf')
                for island_i in island_list_i:
                    for island_j in island_list_j:
                        weight = get_edge_weight(island_i, island_j)
                        if min_distance > weight:
                            min_distance = weight
                self.add_edge(group_name_i, group_name_j, min_distance, True)

    def find_passed_group(self, start, end):
        start_group = self.island_group_map[start]
        end_group = self.island_group_map[end]

        distance = {group: float('inf') for group in self.group_graph}
        distance[start_group] = 0
        priority_queue = [(0, start_group)]

        parent_map = {start_group: None}

        while priority_queue:
            current_distance, current_group = heapq.heappop(priority_queue)

            if current_group == end_group:
                break

            if current_distance > distance[current_group]:
                continue

            for neighbor, weight in self.group_graph.get(current_group, []):
                distance_through_current = current_distance + weight
                if distance_through_current < distance[neighbor]:
                    distance[neighbor] = distance_through_current
                    parent_map[neighbor] = current_group
                    heapq.heappush(priority_queue, (distance_through_current, neighbor))

        if end_group in parent_map:
            path = []
            step = end_group
            while step is not None:
                path.append(step)
                step = parent_map[step]
            path.reverse()
            return path
        else:
            return None

    def find_passed_islands(self, start, end):
        pass_group = self.find_passed_group(start, end)
        if not pass_group:
            return []

        pass_islands = []
        for group in pass_group:
            pass_islands.extend(self.group_island_map[group])
        return pass_islands


class Exchange:
    _weight = {item: 100 for item in level_1_items}
    _weight.update({item: 800 for item in level_2_items})
    _weight.update({item: 900 for item in level_3_items})
    _weight.update({item: 1000 for item in level_4_items + level_5_items})

    def __init__(self, source, target, ratio, swap_cost=11485, trades=None):
        self.source = source
        self.target = target
        self.ratio = ratio
        self.swap_cost = swap_cost
        self.weight = self._weight.get(target, 0)

        self.maximum_exchange = 10
        if target in level_5_items:
            self.maximum_exchange = 6

        self.level = 1
        if target in level_2_items:
            self.level = 2
        elif target in level_3_items:
            self.level = 3
        elif target in level_4_items:
            self.level = 4
        elif target in level_5_items:
            self.level = 5

        self.trades = trades if trades else self.maximum_exchange
        self.remain_exchange = self.init_remain_exchange()

    def init_remain_exchange(self):
        if self.trades > self.maximum_exchange:
            return self.maximum_exchange
        return self.trades


class Stock:
    def __init__(self, stock=None):
        if stock is None:
            stock = {}

        all_items = level_1_items + level_2_items + level_3_items + level_4_items + level_5_items
        self._stock = stock.copy()
        unset_items = set(all_items) - set(stock.keys())
        self._stock.update({item: 0 for item in unset_items})
        self._calc_stock = self._stock.copy()
        self.stock = self._calc_stock

    def __getitem__(self, item):
        return self.stock.get(item, 0)

    def switch_stock(self, is_calc=False):
        self.stock = self._calc_stock if is_calc else self._stock

    def execute_exchange(self, exchange: Exchange, trades):
        if exchange.level != 1:
            self.stock[exchange.source] -= trades
        self.stock[exchange.target] += trades * exchange.ratio


class ExchangeGraph:
    def __init__(self, start_island, ship_load_capacity, stock: Stock, island_graph: IslandGraph):
        self.graph = {}
        self.ship_load_capacity = ship_load_capacity
        self.stock = stock
        self.island_graph = island_graph
        self.start_island = start_island

    def add_trade(self, exchanges: dict):
        for island, args in exchanges.items():
            self.graph[island] = Exchange(*args)
        # print('add_trade')
        # pprint(self.graph)

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
        # for k, v in sorted_graph.items():
        #     print('sorted_graph', k, v.source)

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
        # print('pick_island')
        selections = []

        sorted_overlap = dict(sorted(overlap.items(), key=lambda x: len(x[1])))

        # print('sorted_overlap', sorted_overlap)

        def pick(index):
            print('keys', list(sorted_overlap.keys()))
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

            # print('first_island', first_island)
            for island, island_list in target_overlap.items():
                # print(island, island_list)

                for i, nearby_island in enumerate(island_list):
                    if nearby_island in selections:
                        continue
                    selections.append(nearby_island)
                    break

        max_count = 50
        index = 0
        pick(index)
        # print('selections1', selections)
        while len(selections) != len(overlap) and index < max_count:
            selections = []
            index += 1
            pick(index)

        # print('selections2', selections)
        return {selections[i]: k for i, k in enumerate(sorted_overlap.keys())}

    def get_exchange_weight(self, exchange: Exchange, trades=None):
        if exchange.level == 1:
            return 1000

        available_exchange = exchange.maximum_exchange if trades is None else trades
        if available_exchange > self.stock[exchange.source]:
            available_exchange = self.stock[exchange.source]
        return available_exchange * exchange.ratio * exchange.weight

    def schedule_routes(self):
        sorted_graph = dict(sorted(self.graph.items(), key=lambda x: self.get_exchange_weight(x[1]), reverse=True))
        routes = {}

        def find_routes(index, graph):
            if not graph:
                return

            routes[f'group_{index}'] = {}
            current_island = next(iter(graph))
            current_exchange = graph[current_island]

            # print('=' * 42)
            # print('main', current_exchange.source, 'to', current_exchange.target)

            remain_weight = self.ship_load_capacity

            max_allowable_exchange = self.count_max_allowable_exchange(current_exchange)
            # print('max_allowable_exchange', max_allowable_exchange)

            # execute exchange
            self.stock.execute_exchange(current_exchange, max_allowable_exchange)
            current_exchange.remain_exchange -= max_allowable_exchange
            remain_weight -= max_allowable_exchange * current_exchange.ratio * current_exchange.weight

            routes[f'group_{index}'].update({
                current_island: {
                    'source': current_exchange.source,
                    'exchange': max_allowable_exchange,
                    'target': current_exchange.target,
                }
            })

            # 還有剩就拿出來排最後面
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

                # print('merge', merge_exchange.source, 'to', merge_exchange.target)
                # print('available_merge_trades', available_merge_trades)
                # print('nearby_exchange', nearby_exchange.weight)
                # print('available_merge_trades', available_merge_trades)

                self.stock.execute_exchange(merge_exchange, available_merge_trades)
                remain_weight -= available_merge_trades * merge_exchange.ratio * merge_exchange.weight
                merge_exchange.remain_exchange -= available_merge_trades

                # print('remain_weight', remain_weight)

                graph.pop(merge_island)
                if merge_exchange.remain_exchange > 0:
                    graph[merge_island] = merge_exchange

                routes[f'group_{index}'].update({
                    merge_island: {
                        'source': merge_exchange.source,
                        'exchange': available_merge_trades,
                        'target': merge_exchange.target,
                    }
                })

                # print('櫻花庫存', self.stock['櫻花'])

                if remain_weight <= 0:
                    break

            find_routes(index + 1, graph)

        find_routes(0, sorted_graph)

        # print('==============routes================')
        # for group, route_path in routes.items():
        #     print(f'******* {group} *********')
        #     for island, exchange in route_path.items():
        #         pprint(island)
        #         pprint(exchange)

        # print('================stock================')
        # pprint(self.stock.stock)

        # for island, exchange in self.graph.items():
        #     print(exchange.source, 'to', exchange.target, exchange.remain_exchange)

        return routes

    def tune(self):
        pass
        # tune 最佳解 => 路程最少

