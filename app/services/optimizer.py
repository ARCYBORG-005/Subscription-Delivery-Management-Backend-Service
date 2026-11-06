from dataclasses import dataclass

from ortools.constraint_solver import pywrapcp, routing_enums_pb2


@dataclass(frozen=True)
class StopInput:
    customer_id: int
    name: str
    latitude: float
    longitude: float
    demand_milliliters: int
    traffic_severity: float


@dataclass(frozen=True)
class OptimizedStop:
    stop: StopInput
    sequence: int
    estimated_arrival_minutes: int


@dataclass(frozen=True)
class OptimizationResult:
    stops: list[OptimizedStop]
    estimated_travel_minutes: int


def optimize_single_agent_route(
    stops: list[StopInput],
    travel_time_matrix: list[list[int]],
    capacity_milliliters: int,
    traffic_penalty_weight: int,
) -> OptimizationResult:
    if not stops:
        return OptimizationResult(stops=[], estimated_travel_minutes=0)

    expected_size = len(stops) + 1
    if len(travel_time_matrix) != expected_size or any(
        len(row) != expected_size for row in travel_time_matrix
    ):
        raise ValueError("Travel-time matrix must include depot and every eligible stop")

    manager = pywrapcp.RoutingIndexManager(expected_size, 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def travel_time(from_index: int, to_index: int) -> int:
        return travel_time_matrix[manager.IndexToNode(from_index)][
            manager.IndexToNode(to_index)
        ]

    travel_callback = routing.RegisterTransitCallback(travel_time)
    routing.SetArcCostEvaluatorOfAllVehicles(travel_callback)

    demands = [0, *(stop.demand_milliliters for stop in stops)]

    def demand(index: int) -> int:
        return demands[manager.IndexToNode(index)]

    demand_callback = routing.RegisterUnaryTransitCallback(demand)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback, 0, [capacity_milliliters], True, "Capacity"
    )

    def one_visit_per_arc(from_index: int, to_index: int) -> int:
        del from_index, to_index
        return 1

    visit_callback = routing.RegisterTransitCallback(one_visit_per_arc)
    routing.AddDimension(visit_callback, 0, expected_size, True, "VisitOrder")
    visit_order = routing.GetDimensionOrDie("VisitOrder")
    for node, stop in enumerate(stops, start=1):
        index = manager.NodeToIndex(node)
        desired_position = 1 + round(stop.traffic_severity * (len(stops) - 1))
        visit_order.SetCumulVarSoftLowerBound(
            index, desired_position, traffic_penalty_weight
        )

    parameters = pywrapcp.DefaultRoutingSearchParameters()
    parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    parameters.time_limit.FromSeconds(2)
    solution = routing.SolveWithParameters(parameters)
    if solution is None:
        raise RuntimeError("OR-Tools could not find a feasible route")

    result: list[OptimizedStop] = []
    elapsed_minutes = 0
    index = routing.Start(0)
    sequence = 1
    while not routing.IsEnd(index):
        previous_index = index
        index = solution.Value(routing.NextVar(index))
        if routing.IsEnd(index):
            elapsed_minutes += travel_time_matrix[
                manager.IndexToNode(previous_index)
            ][manager.IndexToNode(index)]
            break
        elapsed_minutes += travel_time_matrix[
            manager.IndexToNode(previous_index)
        ][manager.IndexToNode(index)]
        stop = stops[manager.IndexToNode(index) - 1]
        result.append(
            OptimizedStop(
                stop=stop,
                sequence=sequence,
                estimated_arrival_minutes=elapsed_minutes,
            )
        )
        sequence += 1

    return OptimizationResult(
        stops=result, estimated_travel_minutes=elapsed_minutes
    )
