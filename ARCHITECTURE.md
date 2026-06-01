# Architecture

## Overview

The scheduler assigns charging stops to buses travelling between Bengaluru and Kochi.

For each bus:

1. Find all valid charging plans based on battery range.
2. Estimate waiting time at charging stations.
3. Calculate a score using the configured weights.
4. Choose the plan with the lowest score.
5. Reserve charging slots at the selected stations.

The goal is to reduce waiting time while avoiding charger conflicts.

## Main Components

### scheduler.py

Contains the scheduling logic and data models.

Key responsibilities:

* Generate valid charging plans
* Track charger availability
* Calculate waiting times
* Select the best charging plan

### loader.py

Reads scenario JSON files and converts them into Python objects used by the scheduler.

### app.py

Provides a Streamlit interface to:

* Select scenarios
* View schedules
* View charging station usage
* Compare wait times

## Scenario Configuration

All scenario data is stored in JSON files.

Each scenario contains:

* Route information
* Charging stations
* Bus details
* Physics settings
* Cost weights

Example:

```json
{
  "weights": {
    "individual": 1.0,
    "operator": 1.0,
    "overall": 1.0
  }
}
```

Changing values in the JSON file automatically affects scheduling results.

## Assumptions

* Buses start fully charged.
* Charging always fills the battery completely.
* Travel speed remains constant.
* Charging duration is fixed.
* Charger allocation follows first-come, first-served behaviour.

## Future Improvements

Some possible enhancements:

* Partial charging support
* Dynamic traffic conditions
* Time-based electricity pricing
* Priority buses
* Multiple routes sharing chargers
* Different battery capacities per bus
