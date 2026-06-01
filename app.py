import os
import streamlit as st
import pandas as pd

from loader import list_scenarios, load_scenario, parse_scenario, fmt_time
from scheduler import schedule

SCENARIOS_DIR = os.path.join(os.path.dirname(__file__), "scenarios")

st.set_page_config(
    page_title="Bus Charging Scheduler",
    page_icon="⚡",
    layout="wide",
)

st.markdown("""
<style>
  .block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
  }
</style>
""", unsafe_allow_html=True)

OPERATOR_COLORS = {
    "kpn": "#2563eb",
    "freshbus": "#16a34a",
    "flixbus": "#9333ea",
}

DIRECTION_LABEL = {
    "BK": "Bengaluru → Kochi",
    "KB": "Kochi → Bengaluru",
}


def _minutes_label(m: float) -> str:
    if m < 1:
        return "—"
    return f"{int(round(m))} min"


scenarios = list_scenarios(SCENARIOS_DIR)
display_names = [s[0] for s in scenarios]
paths = [s[1] for s in scenarios]

st.title("Bus Charging Scheduler")

col_sel, col_info = st.columns([3, 2])

with col_sel:
    selected_index = st.selectbox(
        "Select scenario",
        range(len(display_names)),
        format_func=lambda i: display_names[i],
    )

raw = load_scenario(paths[selected_index])
route, stations, physics, weights, buses, meta = parse_scenario(raw)

with col_info:
    st.markdown(f"**{meta['name']}**  \n{meta['description']}")

schedules, queues = schedule(
    buses,
    route,
    stations,
    physics,
    weights,
)

st.markdown("---")
st.subheader("Scenario Input")

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("**Route**")

    route_rows = [
        {
            "From": seg.from_node,
            "To": seg.to_node,
            "Distance (km)": seg.distance_km,
        }
        for seg in route.segments
    ]

    st.dataframe(
        pd.DataFrame(route_rows),
        hide_index=True,
        use_container_width=True,
    )

with c2:
    st.markdown("**Physics & Weights**")

    st.markdown(f"""
| Parameter | Value |
|---|---|
| Battery range | {physics.battery_range_km} km |
| Charge duration | {physics.charge_duration_min} min |
| Speed | {physics.speed_kmh} km/h |
| Weight: individual | {weights.individual} |
| Weight: operator | {weights.operator} |
| Weight: overall | {weights.overall} |
""")

with c3:
    st.markdown("**Stations**")

    station_rows = [
        {
            "ID": s.id,
            "Name": s.name,
            "Chargers": s.num_chargers,
        }
        for s in stations
    ]

    st.dataframe(
        pd.DataFrame(station_rows),
        hide_index=True,
        use_container_width=True,
    )

st.markdown("**Bus Departures**")

bus_rows = [
    {
        "Bus ID": b.id,
        "Operator": b.operator.upper(),
        "Direction": DIRECTION_LABEL[b.direction],
        "Departure": fmt_time(b.departure_min),
    }
    for b in sorted(buses, key=lambda b: (b.direction, b.departure_min))
]

st.dataframe(
    pd.DataFrame(bus_rows),
    hide_index=True,
    use_container_width=True,
)

st.markdown("---")
st.subheader("Per-Bus Timetable")

rows = []

for bus in sorted(buses, key=lambda b: (b.direction, b.departure_min)):
    sched = schedules[bus.id]

    for i, stop in enumerate(sched.stops):
        rows.append({
            "Bus ID": bus.id,
            "Operator": bus.operator.upper(),
            "Direction": DIRECTION_LABEL[bus.direction],
            "Departure": fmt_time(sched.departure_min),
            "Stop #": i + 1,
            "Station": stop.station_id,
            "Arrive": fmt_time(stop.arrive_time),
            "Wait": _minutes_label(stop.wait_time),
            "Charge Start": fmt_time(stop.charge_start),
            "Charge End": fmt_time(stop.charge_end),
        })

timetable_df = pd.DataFrame(rows)

compact_rows = []

for bus in sorted(buses, key=lambda b: (b.direction, b.departure_min)):
    sched = schedules[bus.id]

    stop_summary = " → ".join(
        f"{s.station_id}(+{_minutes_label(s.wait_time)})"
        for s in sched.stops
    )

    compact_rows.append({
        "Bus": bus.id,
        "Op": bus.operator.upper(),
        "Dir": "BK→" if bus.direction == "BK" else "←KB",
        "Depart": fmt_time(sched.departure_min),
        "Charging stops (wait)": stop_summary,
        "Arrive": fmt_time(sched.arrival_time),
        "Total wait": _minutes_label(sched.total_wait_min),
    })

st.dataframe(
    pd.DataFrame(compact_rows),
    hide_index=True,
    use_container_width=True,
)

with st.expander("Detailed stop-by-stop timetable"):
    st.dataframe(
        timetable_df,
        hide_index=True,
        use_container_width=True,
    )

st.markdown("---")
st.subheader("Per-Station Charge Order")

station_cols = st.columns(len(stations))

for col, station in zip(station_cols, stations):
    with col:
        st.markdown(
            f"**Station {station.id}** "
            f"({station.num_chargers} charger"
            f"{'s' if station.num_chargers > 1 else ''})"
        )

        log = queues[station.id].log()

        if not log:
            st.caption("No buses charged here.")
            continue

        station_rows = []

        for rank, (bus_id, arrive, start, end) in enumerate(log, 1):
            bus_spec = next(b for b in buses if b.id == bus_id)

            station_rows.append({
                "#": rank,
                "Bus": bus_id,
                "Op": bus_spec.operator.upper(),
                "Arrive": fmt_time(arrive),
                "Start": fmt_time(start),
                "End": fmt_time(end),
                "Wait": _minutes_label(start - arrive),
            })

        st.dataframe(
            pd.DataFrame(station_rows),
            hide_index=True,
            use_container_width=True,
        )

st.markdown("---")
st.subheader("Summary")

total_wait = sum(s.total_wait_min for s in schedules.values())
max_wait = max(s.total_wait_min for s in schedules.values())
buses_with_wait = sum(
    1 for s in schedules.values()
    if s.total_wait_min > 0
)

c1, c2, c3 = st.columns(3)

c1.metric("Total fleet wait", f"{int(total_wait)} min")
c2.metric("Max single-bus wait", f"{int(max_wait)} min")
c3.metric("Buses that waited", f"{buses_with_wait} / {len(buses)}")

op_data = {}

for sched in schedules.values():
    op_data.setdefault(sched.operator, []).append(
        sched.total_wait_min
    )

op_rows = [
    {
        "Operator": op.upper(),
        "Buses": len(waits),
        "Total wait (min)": int(sum(waits)),
        "Avg wait (min)": f"{sum(waits)/len(waits):.1f}",
        "Max wait (min)": int(max(waits)),
    }
    for op, waits in sorted(op_data.items())
]

st.dataframe(
    pd.DataFrame(op_rows),
    hide_index=True,
    use_container_width=True,
)