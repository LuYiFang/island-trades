import heapq
import json
import logging
import math
import os
import pickle
from collections import defaultdict
from pprint import pprint
from typing import TypeVar, Optional

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from exchange_items import trade_items, island_position

import networkx as nx
import matplotlib.pyplot as plt

T = TypeVar('T', bound='Save')


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


class IslandGraph(Save):
    def __init__(self):
        super().__init__()
        self.island_positions = island_position.copy()

        if not self.__dict__.get('graph'):
            self.graph = {}
            self.create_graph_from_positions(self.graph, self.island_positions)

        if not self.__dict__.get('group_graph'):
            self.group_graph = {}

        if not self.__dict__.get('island_group_map'):
            self.island_group_map = {}

        if not self.__dict__.get('group_island_map'):
            self.group_island_map = {}

        if not self.__dict__.get('group_position'):
            self.cluster_islands(draw=True)

            self.group_position = self.calculate_group_centroids()

            self.group_position = self.calculate_group_centroids()
            self.create_graph_from_positions(self.group_graph, self.group_position, 20, draw=True)

        self.save()

    def add_island(self, island, x, y):
        self.island_positions[island] = (x, y)
        if island not in self.graph:
            self.graph[island] = []

    @staticmethod
    def calculate_distance(island1, island2, position_map):
        x1, y1 = position_map[island1]
        x2, y2 = position_map[island2]
        return np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def create_graph_from_positions(self, graph_map, position_map, max_distance=9, draw=False):
        islands = list(position_map.keys())
        for i, island1 in enumerate(islands):
            for j, island2 in enumerate(islands):
                if i == j:
                    continue
                distance = self.calculate_distance(island1, island2, position_map)
                if distance <= max_distance:
                    self.add_edge(island1, island2, distance, graph_map)

        if draw:
            self.draw_graph(graph_map, position_map)

    @staticmethod
    def add_edge(u, v, weight, graph_map):
        if u not in graph_map:
            graph_map[u] = []
        graph_map[u].append((v, float(weight)))

        if v not in graph_map:
            graph_map[v] = []
        graph_map[v].append((u, float(weight)))

    @staticmethod
    def draw_graph(graph_map, position_map):

        nx_graph = nx.Graph()

        for island, neighbors in graph_map.items():
            for neighbor in neighbors:
                nx_graph.add_edge(island, neighbor[0], weight=neighbor[1])

        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False

        nx.draw(nx_graph, position_map, with_labels=True, node_size=500, node_color="skyblue", font_size=10,
                font_color="black", font_weight="bold", edge_color="gray")
        plt.show()

    def nearby_islands(self, island, max_distance):
        nearby = []
        for neighbor, weight in self.graph[island]:
            if weight <= max_distance:
                nearby.append(neighbor)
        return nearby

    def cluster_islands(self, num_clusters=15, draw=False):
        islands = list(self.island_positions.keys())
        coordinates = np.array(list(self.island_positions.values()))
        scaler = StandardScaler()
        scaled_coordinates = scaler.fit_transform(coordinates)

        k_means = KMeans(n_clusters=num_clusters).fit(scaled_coordinates)
        labels = k_means.labels_

        if draw:
            self.draw_clustering(labels, coordinates, islands)

        group = defaultdict(list)
        for i, label in enumerate(labels):
            group[f'group_{label}'].append(islands[i])
            self.island_group_map[islands[i]] = f'group_{label}'
        self.group_island_map = group

    @staticmethod
    def draw_clustering(labels, coordinates, islands):
        colors = ['r', 'g', 'b', 'c', 'm', 'y', 'k', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'indigo']
        for i, label in enumerate(labels):
            plt.scatter(coordinates[i][0], coordinates[i][1], color=colors[label % len(colors)])
            plt.text(float(coordinates[i][0]), float(coordinates[i][1]), islands[i], fontsize=12)

        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False
        plt.xlabel('X')
        plt.ylabel('Y')
        plt.title('Island Clusters')
        plt.legend()
        plt.show()

    def calculate_group_centroids(self):
        group_centroids = {}
        for group, islands in self.group_island_map.items():
            x_coords = [self.island_positions[island][0] for island in islands]
            y_coords = [self.island_positions[island][1] for island in islands]
            centroid_x = sum(x_coords) / len(x_coords)
            centroid_y = sum(y_coords) / len(y_coords)
            group_centroids[group] = (centroid_x, centroid_y)
        return group_centroids

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
        pass_islands.remove(end)
        return pass_islands

    def save(self):
        super().save(
            'graph',
            'group_graph',
            'island_group_map',
            'group_island_map',
            'group_position',
        )


class Exchange:
    def __init__(self, island, source, target, ratio, swap_cost=11485, trades=None, level=None, weight=0):
        self.island = island
        self.source = source
        self.target = target
        self.ratio = ratio
        self.swap_cost = swap_cost
        self.weight = weight

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


class Stock(Save):
    def __init__(self):
        super().__init__()

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

        all_items = [item['name'] for items in self.trade_items.values() for item in items]

        if not self.__dict__.get('_stock'):
            self._stock = {}

        unset_items = set(all_items) - set(self._stock.keys())
        self._stock.update({item: 0 for item in unset_items})
        self._calc_stock = self._stock.copy()
        self.stock = self._calc_stock
        self.ori_stock = self._stock.copy()

        self.item_level = self.update_item_level()
        self.item_weight = self.update_item_weight()

    def __getitem__(self, item):
        return self.stock.get(item, 0)

    def __setitem__(self, key, value):
        self.stock[key] = value

    def switch_stock(self, is_calc=False):
        self.stock = self._calc_stock if is_calc else self._stock

    def execute_exchange(self, exchange: Exchange, trades):
        if exchange.level != 1:
            self.stock[exchange.source] -= trades
        self.stock[exchange.target] += trades * exchange.ratio

    def undo_execute_exchange(self, exchange: Exchange, trades):
        if exchange.level != 1:
            self.stock[exchange.source] += trades
        self.stock[exchange.target] -= trades * exchange.ratio

    def restore(self):
        self._stock = self.ori_stock.copy()
        self._calc_stock = self.ori_stock.copy()

    def update_trade_items(self, level, item):
        self.trade_items[level].append({'name': item})
        self.item_level = self.update_item_level()
        self.item_weight = self.update_item_weight()

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
                weight = 100
                if level == 2:
                    weight = 800
                elif level == 3:
                    weight = 900
                elif level == 4 or level == 5:
                    weight = 1000
                item_weight[item['name']] = weight
        return item_weight

    def save(self):
        super().save(
            'trade_items',
            '_stock',
        )


class ExchangeGraph(Save):
    def __init__(self, start_island, ship_load_capacity, stock: Stock, island_graph: IslandGraph):
        super().__init__()
        self.graph = {}
        self.ship_load_capacity = ship_load_capacity
        self.stock = stock
        self.island_graph = island_graph
        self.start_island = start_island

    def add_trade(self, exchanges: dict):
        for island, args in exchanges.items():
            level = self.stock.item_level.get(args[1])
            weight = self.stock.item_weight.get(args[1])
            self.graph[island] = Exchange(island, *args, level, weight)
        self.save('graph')

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

                # print('櫻花庫存', self.stock['櫻花'])

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
        # tune 最佳解 => 路程最少
