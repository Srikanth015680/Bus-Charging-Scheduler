from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import heapq
import itertools

@dataclass
class Segment:
    from_node: str
    to_node: str
    distance_km: float


@dataclass
class Station:
    id: str
    name: str
    num_chargers: int = 1


@dataclass
class Physics:
    battery_range_km: float
    charge_duration_min: float
    speed_kmh: float

    def travel_time_min(self, distance_km: float) -> float:
        return (distance_km / self.speed_kmh) * 60.0


@dataclass
class Weights:
    individual: float = 1.0
    operator: float = 1.0
    overall: float = 1.0


@dataclass
class BusSpec:
    id: str
    operator: str
    direction: str          
    departure_min: float    


@dataclass
class Route:
    id: str
    name: str
    origin: str
    destination: str
    segments: List[Segment]

    def ordered_stops(self) -> List[str]:
        stops = [self.segments[0].from_node]
        for seg in self.segments:
            stops.append(seg.to_node)
        return stops

    def distance_between(self, a: str, b: str) -> Optional[float]:
        stops = self.ordered_stops()
        if a not in stops or b not in stops:
            return None
        ia, ib = stops.index(a), stops.index(b)
        if ia >= ib:
            return None
        total = 0.0
        for seg in self.segments[ia:ib]:
            total += seg.distance_km
        return total

    def segment_distance(self, from_node: str, to_node: str) -> float:
        for seg in self.segments:
            if seg.from_node == from_node and seg.to_node == to_node:
                return seg.distance_km
        raise ValueError(f"No segment {from_node}→{to_node}")



@dataclass
class ChargingStop:
    station_id: str
    arrive_time: float      
    wait_time: float        
    charge_start: float     
    charge_end: float      
    depart_time: float      


@dataclass
class BusSchedule:
    bus_id: str
    operator: str
    direction: str
    departure_min: float
    origin: str
    destination: str
    stops: List[ChargingStop]   
    arrival_time: float          
    total_wait_min: float        

    def stop_for_station(self, station_id: str) -> Optional[ChargingStop]:
        for s in self.stops:
            if s.station_id == station_id:
                return s
        return None



def build_travel_context(bus: BusSpec, route: Route, stations: List[Station]):
   
    stops = route.ordered_stops()
    station_ids = {s.id for s in stations}
    intermediate = [n for n in stops if n in station_ids]
    if bus.direction == "BK":
        return intermediate         
    else:
        return list(reversed(intermediate))  


def enumerate_valid_plans(
    bus: BusSpec,
    route: Route,
    stations: List[Station],
    physics: Physics,
) -> List[List[str]]:
    
    stops = route.ordered_stops()
    ordered_route = stops if bus.direction == "BK" else list(reversed(stops))

    station_ids = {s.id for s in stations}
    candidate_stations = [n for n in ordered_route if n in station_ids]

   
    origin = ordered_route[0]
    dest = ordered_route[-1]
    R = physics.battery_range_km

    def dist(a: str, b: str) -> float:
        ia = ordered_route.index(a)
        ib = ordered_route.index(b)
        total = 0.0
        for i in range(ia, ib):
            fn = ordered_route[i]
            tn = ordered_route[i + 1]
            if bus.direction == "BK":
                total += route.segment_distance(fn, tn)
            else:
                total += route.segment_distance(tn, fn)
        return total

    valid_plans: List[List[str]] = []
    n = len(candidate_stations)
    for r in range(1, n + 1):
        for combo in itertools.combinations(candidate_stations, r):
            plan = list(combo)
            checkpoints = [origin] + plan + [dest]
            feasible = True
            for i in range(len(checkpoints) - 1):
                d = dist(checkpoints[i], checkpoints[i + 1])
                if d > R:
                    feasible = False
                    break
            if feasible:
                valid_plans.append(plan)

    return valid_plans



def cost_individual(wait_min: float) -> float:
    return wait_min


def cost_operator(
    wait_min: float,
    operator: str,
    all_schedules: Dict[str, BusSchedule],
) -> float:
   
    op_waits = [s.total_wait_min for s in all_schedules.values()
                if s.operator == operator]
    if not op_waits:
        return wait_min
    fleet_avg = sum(op_waits) / len(op_waits)
    deviation = max(0.0, wait_min - fleet_avg)
    return deviation


def cost_overall(wait_min: float) -> float:
    return wait_min


def composite_cost(
    wait_min: float,
    bus_id: str,
    operator: str,
    all_schedules: Dict[str, BusSchedule],
    weights: Weights,
) -> float:
    
    c_ind = weights.individual * cost_individual(wait_min)
    c_op  = weights.operator   * cost_operator(wait_min, operator, all_schedules)
    c_all = weights.overall    * cost_overall(wait_min)
    return c_ind + c_op + c_all



class StationQueue:
    
    def __init__(self, station_id: str, num_chargers: int, charge_duration: float):
        self.station_id = station_id
        self.num_chargers = num_chargers
        self.charge_duration = charge_duration
        self._free_times: List[float] = [0.0] * num_chargers
        heapq.heapify(self._free_times)
        self._log: List[Tuple[str, float, float, float]] = []  

    def schedule(self, bus_id: str, arrive_time: float) -> Tuple[float, float, float]:
        
        earliest_free = heapq.heappop(self._free_times)
        charge_start = max(arrive_time, earliest_free)
        wait_min = charge_start - arrive_time
        charge_end = charge_start + self.charge_duration
        heapq.heappush(self._free_times, charge_end)
        self._log.append((bus_id, arrive_time, charge_start, charge_end))
        return wait_min, charge_start, charge_end

    def log(self) -> List[Tuple[str, float, float, float]]:
        return sorted(self._log, key=lambda x: x[2]) 



def schedule(
    buses: List[BusSpec],
    route: Route,
    stations: List[Station],
    physics: Physics,
    weights: Weights,
) -> Tuple[Dict[str, BusSchedule], Dict[str, StationQueue]]:
    station_map = {s.id: s for s in stations}
    queues: Dict[str, StationQueue] = {
        s.id: StationQueue(s.id, s.num_chargers, physics.charge_duration_min)
        for s in stations
    }

    scheduled: Dict[str, BusSchedule] = {}

    stops_full = route.ordered_stops()

    def ordered_route_for(bus: BusSpec) -> List[str]:
        return stops_full if bus.direction == "BK" else list(reversed(stops_full))

    def arrival_at_first_candidate(bus: BusSpec) -> float:
        ordered = ordered_route_for(bus)
        station_ids = {s.id for s in stations}
        cands = [n for n in ordered if n in station_ids]
        if not cands:
            return bus.departure_min
        dist_to_first = sum_distance_along(bus, route, ordered[0], cands[0])
        return bus.departure_min + physics.travel_time_min(dist_to_first)

    def sum_distance_along(bus: BusSpec, route: Route, a: str, b: str) -> float:
        ordered = ordered_route_for(bus)
        ia, ib = ordered.index(a), ordered.index(b)
        total = 0.0
        for i in range(ia, ib):
            fn, tn = ordered[i], ordered[i + 1]
            if bus.direction == "BK":
                total += route.segment_distance(fn, tn)
            else:
                total += route.segment_distance(tn, fn)
        return total

    sorted_buses = sorted(buses, key=lambda b: arrival_at_first_candidate(b))

    for bus in sorted_buses:
        ordered = ordered_route_for(bus)
        origin, dest = ordered[0], ordered[-1]

        valid_plans = enumerate_valid_plans(bus, route, stations, physics)
        if not valid_plans:
            raise ValueError(f"Bus {bus.id}: no valid charging plan found.")

        best_plan = None
        best_cost = float("inf")
        best_stops: List[ChargingStop] = []

        for plan in valid_plans:
            current_time = bus.departure_min
            current_pos = origin
            stops_sim: List[ChargingStop] = []
            total_wait = 0.0

            for station_id in plan:
                dist = sum_distance_along(bus, route, current_pos, station_id)
                travel = physics.travel_time_min(dist)
                arrive = current_time + travel
                q = queues[station_id]
                sorted_free = sorted(q._free_times)
                charge_start = max(arrive, sorted_free[0])
                wait = charge_start - arrive
                charge_end = charge_start + physics.charge_duration_min

                stops_sim.append(ChargingStop(
                    station_id=station_id,
                    arrive_time=arrive,
                    wait_time=wait,
                    charge_start=charge_start,
                    charge_end=charge_end,
                    depart_time=charge_end,
                ))
                total_wait += wait
                current_time = charge_end
                current_pos = station_id

         
            c = composite_cost(total_wait, bus.id, bus.operator, scheduled, weights)
            if c < best_cost:
                best_cost = c
                best_plan = plan
                best_stops = stops_sim

        committed_stops: List[ChargingStop] = []
        current_time = bus.departure_min
        current_pos = origin
        for stop_sim in best_stops:
            wait, charge_start, charge_end = queues[stop_sim.station_id].schedule(
                bus.id, stop_sim.arrive_time
            )
            committed_stops.append(ChargingStop(
                station_id=stop_sim.station_id,
                arrive_time=stop_sim.arrive_time,
                wait_time=wait,
                charge_start=charge_start,
                charge_end=charge_end,
                depart_time=charge_end,
            ))
            current_time = charge_end
            current_pos = stop_sim.station_id

        dist_to_dest = sum_distance_along(bus, route, current_pos, dest)
        arrival = current_time + physics.travel_time_min(dist_to_dest)
        total_wait = sum(s.wait_time for s in committed_stops)

        scheduled[bus.id] = BusSchedule(
            bus_id=bus.id,
            operator=bus.operator,
            direction=bus.direction,
            departure_min=bus.departure_min,
            origin=origin,
            destination=dest,
            stops=committed_stops,
            arrival_time=arrival,
            total_wait_min=total_wait,
        )

    return scheduled, queues
