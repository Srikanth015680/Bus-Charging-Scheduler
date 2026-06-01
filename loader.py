from __future__ import annotations

import json
import os
from typing import List, Tuple, Dict, Any

from scheduler import (
    BusSpec,
    Route,
    Segment,
    Station,
    Physics,
    Weights,
)


def _parse_time(t: str) -> float:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _fmt_time(minutes: float) -> str:
    minutes = int(round(minutes))
    h = (minutes // 60) % 24
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def load_scenario(path: str) -> Dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def parse_scenario(raw: Dict[str, Any]):
    meta = {
        "id": raw["id"],
        "name": raw["name"],
        "description": raw.get("description", ""),
    }

    segments = [
        Segment(
            s["from"],
            s["to"],
            s["distance_km"]
        )
        for s in raw["route"]["segments"]
    ]

    route = Route(
        id=raw["route"]["id"],
        name=raw["route"]["name"],
        origin=raw["route"]["origin"],
        destination=raw["route"]["destination"],
        segments=segments,
    )

    stations = [
        Station(
            s["id"],
            s["name"],
            s.get("num_chargers", 1),
        )
        for s in raw["stations"]
    ]

    physics_data = raw["physics"]

    physics = Physics(
        battery_range_km=physics_data["battery_range_km"],
        charge_duration_min=physics_data["charge_duration_min"],
        speed_kmh=physics_data["speed_kmh"],
    )

    weight_data = raw.get("weights", {})

    weights = Weights(
        individual=weight_data.get("individual", 1.0),
        operator=weight_data.get("operator", 1.0),
        overall=weight_data.get("overall", 1.0),
    )

    buses = [
        BusSpec(
            id=bus["id"],
            operator=bus["operator"],
            direction=bus["direction"],
            departure_min=_parse_time(bus["departure"]),
        )
        for bus in raw["buses"]
    ]

    return route, stations, physics, weights, buses, meta


def list_scenarios(scenarios_dir: str) -> List[Tuple[str, str]]:
    files = sorted(
        file_name
        for file_name in os.listdir(scenarios_dir)
        if file_name.endswith(".json")
    )

    scenarios = []

    for file_name in files:
        path = os.path.join(scenarios_dir, file_name)
        raw = load_scenario(path)

        display_name = (
            f"{raw['id'].replace('_', ' ').title()} — "
            f"{raw['name']}"
        )

        scenarios.append((display_name, path))

    return scenarios


def fmt_time(minutes: float) -> str:
    return _fmt_time(minutes)