from math import ceil, radians, sin, cos, sqrt, atan2
from typing import Protocol


Coordinate = tuple[float, float]


class MatrixProvider(Protocol):
    def build_travel_time_matrix(
        self, coordinates: list[Coordinate]
    ) -> list[list[int]]:
        """Return estimated travel times in minutes for every coordinate pair."""


class HaversineMatrixProvider:
    """Local development estimate; replace with a Maps/TomTom provider in production."""

    average_speed_kmh = 25.0
    road_detour_factor = 1.35

    def build_travel_time_matrix(
        self, coordinates: list[Coordinate]
    ) -> list[list[int]]:
        matrix: list[list[int]] = []
        for origin in coordinates:
            row: list[int] = []
            for destination in coordinates:
                distance_km = self._distance_km(origin, destination)
                minutes = distance_km * self.road_detour_factor / self.average_speed_kmh * 60
                row.append(ceil(minutes))
            matrix.append(row)
        return matrix

    @staticmethod
    def _distance_km(origin: Coordinate, destination: Coordinate) -> float:
        lat1, lon1 = map(radians, origin)
        lat2, lon2 = map(radians, destination)
        delta_lat = lat2 - lat1
        delta_lon = lon2 - lon1
        a = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
        return 6371.0 * 2 * atan2(sqrt(a), sqrt(1 - a))
