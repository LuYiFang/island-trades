import heapq
import logging
from collections import defaultdict

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from exchange_items import island_position

import networkx as nx
import matplotlib.pyplot as plt

from utility import Save


class IslandGraph(Save):
    def __init__(self, start_island):
        super().__init__()
        try:
            self.start_island = start_island
            self.island_positions = island_position.copy()

            if not self.__dict__.get('graph'):
                self.graph = {}
                self.create_graph_from_positions(self.graph, self.island_positions, 7, draw=True)

            if not self.__dict__.get('island_group_map'):
                self.island_group_map = {}

            if not self.__dict__.get('group_island_map'):
                self.group_island_map = {}

            if not self.__dict__.get('group_position'):
                self.cluster_islands(draw=True)

                self.group_position = self.calculate_group_centroids()

                self.group_position = self.calculate_group_centroids()

            if not self.__dict__.get('group_graph'):
                self.group_graph = {}
                self.create_graph_from_positions(self.group_graph, self.group_position, 25, draw=True)

            self.save()
        except Exception as e:
            logging.exception(e)

    def add_island(self, island, x, y):
        self.island_positions[island] = (x, y)
        if island not in self.graph:
            self.graph[island] = []

    @staticmethod
    def calculate_distance(island1, island2, position_map):
        x1, y1 = position_map[island1]
        x2, y2 = position_map[island2]
        return np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def calculate_distance_with_start_island(self, island):
        return self.calculate_distance(island, self.start_island, self.island_positions)

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
        plt.figure()
        nx_graph = nx.Graph()

        for island, neighbors in graph_map.items():
            for neighbor in neighbors:
                nx_graph.add_edge(island, neighbor[0], weight=neighbor[1])

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
        self.draw_graph(self.graph, self.island_positions)

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
        self.draw_graph(self.group_graph, self.group_position)

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

    def is_nearby(self, island, neighbor, max_distance=6):
        return self.calculate_distance(island, neighbor, self.island_positions) <= max_distance

    def is_passed_by(self, current_island, visited_islands):
        max_distance = -float('inf')
        farthest_island = self.start_island
        for visited_island in visited_islands:
            dist = self.calculate_distance(self.start_island, visited_island, self.island_positions)
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
            'group_graph',
            'island_group_map',
            'group_island_map',
            'group_position',
        )

    def find_best_path(self, islands):
        source = min(islands, key=lambda x: self.calculate_distance_with_start_island(x))
        target = max(islands, key=lambda x: self.calculate_distance_with_start_island(x))
        nx_graph = nx.Graph()
        for island in islands:
            neighbors = self.graph[island]
            for neighbor in neighbors:
                nx_graph.add_edge(island, neighbor[0], weight=neighbor[1])

        shortest_path = nx.dijkstra_path(nx_graph, source, target)
        return shortest_path


