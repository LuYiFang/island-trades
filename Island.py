import logging
import sys
from collections import defaultdict

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from exchange_items import island_position

import networkx as nx
import networkx.algorithms.approximation as nx_app
import matplotlib.pyplot as plt

from utility import Save


class IslandGraph(Save):
    def __init__(self, start_island):
        super().__init__()
        try:
            self.start_island = start_island
            self.island_positions = island_position.copy()

            self.island_nx_graph = nx.Graph()
            self.group_nx_graph = nx.Graph()

            self.graph = {}
            self.create_graph_from_positions(False, 7)

            if not self.__dict__.get('island_group_map'):
                self.island_group_map = {}

            if not self.__dict__.get('group_island_map'):
                self.group_island_map = {}

            if not self.__dict__.get('group_position'):
                self.cluster_islands(draw=True)

                self.group_position = self.calculate_group_centroids()

                self.group_position = self.calculate_group_centroids()

            self.group_graph = {}
            self.create_graph_from_positions(True, 25)

            self.save()
        except Exception as e:
            logging.exception(e)

    def add_island(self, island, x, y):
        self.island_positions[island] = (x, y)
        if island not in self.graph:
            self.graph[island] = []

    def calculate_distance(self, island1, island2, is_group=False):
        _, position_map, _ = self.get_variable_group(is_group)
        x1, y1 = position_map[island1]
        x2, y2 = position_map[island2]
        return np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def calculate_distance_with_start_island(self, island):
        return self.calculate_distance(island, self.start_island)

    def add_edge(self, u, v, weight, is_group):
        graph_map, _, _ = self.get_variable_group(is_group)

        if u not in graph_map:
            graph_map[u] = []
        graph_map[u].append((v, float(weight)))

        if v not in graph_map:
            graph_map[v] = []
        graph_map[v].append((u, float(weight)))

    def draw_graph(self, is_group):
        graph_map, position_map, nx_graph = self.get_variable_group(is_group)
        plt.figure()

        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False

        nx.draw(nx_graph, position_map, with_labels=True, node_size=500, node_color="skyblue", font_size=10,
                font_color="black", font_weight="bold", edge_color="gray")
        plt.show(block=False)

    @staticmethod
    def draw_clustering(labels, coordinates, islands):
        plt.figure()
        colors = ['r', 'g', 'b', 'c', 'm', 'y', 'k', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'indigo']
        for i, label in enumerate(labels):
            plt.scatter(coordinates[i][0], coordinates[i][1], color=colors[label % len(colors)])
            plt.text(float(coordinates[i][0]), float(coordinates[i][1]), islands[i], fontsize=12)

        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False
        plt.xlabel('X')
        plt.ylabel('Y')
        plt.title('Island Clusters')
        plt.show(block=False)

    def draw_island_graph(self):
        self.draw_graph(False)

    def draw_island_group(self):
        try:
            labels = []
            coordinates = np.array(list(self.island_positions.values()))
            islands = list(self.island_positions.keys())
            special_island_index = 0
            for island in islands:
                group = self.island_group_map[island]
                label = group.replace('group_', '')
                try:
                    label = int(label)
                except ValueError:
                    label = len(islands) + special_island_index
                    special_island_index += 1
                labels.append(label)

            self.draw_clustering(labels, coordinates, islands)
        except Exception as e:
            logging.exception(e)

    def draw_group_graph(self):
        self.draw_graph(True)

    def get_variable_group(self, is_group):
        return self.group_graph if is_group else self.graph, \
               self.group_position if is_group else self.island_positions, \
               self.group_nx_graph if is_group else self.island_nx_graph

    def create_graph_from_positions(self, is_group, max_distance=9):
        graph_map, position_map, nx_graph = self.get_variable_group(is_group)

        islands = list(position_map.keys())
        for i, island1 in enumerate(islands):
            for j, island2 in enumerate(islands):
                if i == j:
                    continue
                distance = self.calculate_distance(island1, island2, is_group)
                if distance <= max_distance:
                    self.add_edge(island1, island2, distance, is_group)
                    nx_graph.add_edge(island1, island2, weight=distance)

    def cluster_islands(self, num_clusters=8, draw=False):
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
            island = islands[i]
            group_name = f'group_{label}'
            if island == self.start_island:
                group_name = f'group_{self.start_island}'
            if island == '貝村':
                group_name = f'group_貝村'
            if island == '艾港':
                group_name = f'group_艾港'
            if island == '澳眼':
                group_name = f'group_澳眼'
            group[group_name].append(islands[i])
            self.island_group_map[islands[i]] = group_name
        self.group_island_map = group

    def calculate_group_centroids(self):
        group_centroids = {}
        for group, islands in self.group_island_map.items():
            x_coords = [self.island_positions[island][0] for island in islands]
            y_coords = [self.island_positions[island][1] for island in islands]
            centroid_x = sum(x_coords) / len(x_coords)
            centroid_y = sum(y_coords) / len(y_coords)
            group_centroids[group] = (centroid_x, centroid_y)
        return group_centroids

    def find_nearby_islands(self, island, max_distance):
        nearby = []
        for neighbor, weight in self.graph[island]:
            if weight <= max_distance:
                nearby.append(neighbor)
        return nearby

    def find_passed_group(self, start, end):
        start_group = self.island_group_map[start]
        end_group = self.island_group_map[end]

        graph_map, position_map, nx_graph = self.get_variable_group(True)
        return nx.dijkstra_path(nx_graph, start_group, end_group)

    def find_passed_islands(self, start, end):
        pass_group = self.find_passed_group(start, end)
        if not pass_group:
            return []

        pass_islands = []
        for group in pass_group:
            pass_islands.extend(self.group_island_map[group])
        pass_islands.remove(end)
        return pass_islands

    def is_nearby(self, island, neighbor, max_distance=6):
        return self.calculate_distance(island, neighbor) <= max_distance

    def is_passed_by(self, current_island, visited_islands):
        max_distance = -float('inf')
        farthest_island = self.start_island
        for visited_island in visited_islands:
            dist = self.calculate_distance(self.start_island, visited_island)
            if max_distance < dist:
                max_distance = dist
                farthest_island = visited_island
        passed_islands = self.find_passed_islands(self.start_island, farthest_island)
        if current_island in passed_islands:
            return True

        passed_islands = self.find_passed_islands(self.start_island, current_island)
        for visited_island in visited_islands:
            if visited_island not in passed_islands:
                return False
        return True

    def is_island_valid(self, current_island, visited_islands):
        if not visited_islands:
            return True

        for visited_island in visited_islands:
            if self.is_nearby(current_island, visited_island):
                return True

        return self.is_passed_by(current_island, visited_islands)

    def save(self):
        super().save(
            'exchanges',
            'island_group_map',
            'group_island_map',
            'group_position',
        )

    def find_best_path(self, islands):
        if len(islands) <= 1:
            return islands

        if sys.version_info.major < 3 or sys.version_info.minor <= 6:
            return islands

        nx_graph = nx.Graph()
        for island in islands:
            for neighbor in islands:
                if island == neighbor:
                    continue

                nx_graph.add_edge(island, neighbor, weight=self.calculate_distance(island, neighbor))

        shortest_path = nx_app.traveling_salesman_problem(nx_graph, cycle=False, method=nx_app.christofides)
        return shortest_path
