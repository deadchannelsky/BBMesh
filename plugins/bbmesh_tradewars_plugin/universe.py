"""
TradeWars Plugin - Universe Generation and Pathfinding
"""

import random
from typing import List, Dict, Optional, Tuple
from collections import deque
import heapq


class UniverseManager:
    """Generates and manages the game universe"""

    TOTAL_SECTORS = 100
    PORTS_COUNT = 30
    PORT_DESCRIPTIONS = [
        "Trading Hub", "Relay Station", "Commercial Port", "Dock",
        "Market Station", "Exchange Point", "Supply Depot", "Outpost"
    ]

    def __init__(self, seed: int = None):
        """Initialize universe manager with optional seed"""
        if seed is not None:
            random.seed(seed)
        self.sectors: Dict[int, List[int]] = {}
        self.ports: set = set()

    def generate_universe(self) -> Dict[int, List[int]]:
        """
        Generate 100-sector universe with 2-3 connections per sector

        Returns:
            Dictionary mapping sector_id -> list of connected_sector_ids
        """
        self.sectors = {}

        # Create all sectors with empty connections initially
        for i in range(1, self.TOTAL_SECTORS + 1):
            self.sectors[i] = []

        # Create connections ensuring connectivity
        # First, create a simple path through all sectors
        for i in range(1, self.TOTAL_SECTORS):
            # Connect sector i to sector i+1
            if i + 1 not in self.sectors[i]:
                self.sectors[i].append(i + 1)
            if i not in self.sectors[i + 1]:
                self.sectors[i + 1].append(i)

        # Add random connections (2-3 per sector on average)
        for sector_id in range(1, self.TOTAL_SECTORS + 1):
            current_connections = len(self.sectors[sector_id])

            # Add 0-2 more random connections
            needed = random.randint(0, 2)
            attempts = 0

            while len(self.sectors[sector_id]) < current_connections + needed and attempts < 10:
                target = random.randint(1, self.TOTAL_SECTORS)

                # Don't connect to self, and limit distance to prevent too-long shortcuts
                if target != sector_id and target not in self.sectors[sector_id]:
                    distance = abs(target - sector_id)
                    # Bias toward nearby connections
                    if distance > 20 and random.random() > 0.3:
                        attempts += 1
                        continue

                    if target not in self.sectors[sector_id]:
                        self.sectors[sector_id].append(target)
                    if sector_id not in self.sectors[target]:
                        self.sectors[target].append(sector_id)

                attempts += 1

        # Sort connections for consistency
        for sector_id in self.sectors:
            self.sectors[sector_id].sort()

        return self.sectors

    def select_port_sectors(self) -> set:
        """Select which sectors have ports"""
        if not self.sectors:
            self.generate_universe()

        # Ensure relatively even distribution
        port_sectors = set()
        step = self.TOTAL_SECTORS // self.PORTS_COUNT

        for i in range(self.PORTS_COUNT):
            base = i * step
            offset = random.randint(0, step - 1)
            sector = base + offset + 1  # +1 because sectors are 1-indexed

            if sector <= self.TOTAL_SECTORS:
                port_sectors.add(sector)

        self.ports = port_sectors
        return port_sectors

    def get_port_name(self, sector_id: int) -> str:
        """Generate port name for sector"""
        desc = random.choice(self.PORT_DESCRIPTIONS)
        return f"{desc}-{sector_id}"

    def find_path(self, start_sector: int, end_sector: int) -> Optional[List[int]]:
        """
        Find shortest path between sectors using Dijkstra's algorithm

        Args:
            start_sector: Starting sector ID
            end_sector: Destination sector ID

        Returns:
            List of sector IDs from start to end, or None if unreachable
        """
        if not self.sectors:
            self.generate_universe()

        if start_sector not in self.sectors or end_sector not in self.sectors:
            return None

        if start_sector == end_sector:
            return [start_sector]

        # Dijkstra's algorithm
        distances = {sector: float('inf') for sector in self.sectors}
        distances[start_sector] = 0
        previous = {sector: None for sector in self.sectors}

        # Priority queue: (distance, sector)
        pq = [(0, start_sector)]

        while pq:
            current_dist, current = heapq.heappop(pq)

            if current == end_sector:
                # Reconstruct path
                path = []
                node = end_sector
                while node is not None:
                    path.append(node)
                    node = previous[node]
                return path[::-1]

            if current_dist > distances[current]:
                continue

            # Check all neighbors
            for neighbor in self.sectors.get(current, []):
                distance = current_dist + 1  # Each warp costs 1 turn

                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous[neighbor] = current
                    heapq.heappush(pq, (distance, neighbor))

        return None  # No path found

    def get_distance(self, start_sector: int, end_sector: int) -> Optional[int]:
        """
        Get minimum distance between sectors

        Returns:
            Number of warps needed, or None if unreachable
        """
        path = self.find_path(start_sector, end_sector)
        if path:
            return len(path) - 1  # Number of warps (not counting start)
        return None

    def get_connected_sectors(self, sector_id: int) -> List[int]:
        """Get list of directly connected sectors"""
        if not self.sectors:
            self.generate_universe()
        return self.sectors.get(sector_id, [])

    def is_connected(self, sector_a: int, sector_b: int) -> bool:
        """Check if two sectors are directly connected"""
        return sector_b in self.get_connected_sectors(sector_a)

    def validate_universe(self) -> bool:
        """Validate that universe is fully connected"""
        if not self.sectors or len(self.sectors) < 2:
            return False

        # BFS from sector 1 to check all reachable
        visited = set()
        queue = deque([1])
        visited.add(1)

        while queue:
            sector = queue.popleft()
            for neighbor in self.sectors.get(sector, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        # Should have visited all sectors
        return len(visited) == self.TOTAL_SECTORS

    def get_nearest_port(self, current_sector: int) -> Optional[Tuple[int, int, int]]:
        """
        Find nearest port to current sector

        Returns:
            Tuple of (port_sector, distance, turns_cost) or None
        """
        if not self.ports:
            self.select_port_sectors()

        nearest_port = None
        nearest_distance = float('inf')

        for port_sector in self.ports:
            distance = self.get_distance(current_sector, port_sector)
            if distance is not None and distance < nearest_distance:
                nearest_distance = distance
                nearest_port = port_sector

        if nearest_port is not None:
            return (nearest_port, nearest_distance, nearest_distance)

        return None

    def get_random_sector(self, avoid_sector: int = None) -> int:
        """Get random sector ID, optionally avoiding one"""
        if not self.sectors:
            self.generate_universe()

        sector = random.randint(1, self.TOTAL_SECTORS)
        if avoid_sector and sector == avoid_sector:
            return self.get_random_sector(avoid_sector)

        return sector

    def get_starting_sector(self) -> int:
        """Get random starting sector (1-10)"""
        return random.randint(1, 10)
