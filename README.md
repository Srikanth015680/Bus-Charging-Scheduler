# Bus Charging Scheduler

This project schedules charging stops for electric buses travelling on a fixed route.

The goal is to reduce waiting time at charging stations while handling situations where multiple buses need the same charger.

A simple Streamlit interface is included to test different scenarios and view the generated schedules.

## Run the Project

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the app:

```bash
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

Select a scenario from the dropdown to view the results.

## Scenarios

All scenarios are stored as JSON files inside the `scenarios` folder.

Each scenario contains:

* Route information
* Charging stations
* Bus schedules
* Battery and charging settings
* Scheduling weights

## Changing Weights

Weights control how the scheduler chooses between charging plans.

Example:

```json
"weights": {
  "individual": 1.0,
  "operator": 2.0,
  "overall": 1.0
}
```

* `individual` reduces wait time for a single bus.
* `operator` balances wait times across buses from the same operator.
* `overall` reduces total waiting time across all buses.

After updating a scenario file, reload the app to see the changes.

## Adding a Scenario

Create a new JSON file inside the `scenarios` folder.

Example:

```bash
cp scenarios/scenario_1.json scenarios/scenario_6.json
```

Update the scenario details and reload the application.

## Project Structure


bus_scheduler/
app.py
scheduler.py
loader.py
requirements.txt
README.md
ARCHITECTURE.md
scenarios/


## Notes

The scheduling logic is separated from the UI so that new scenarios and scheduling rules can be tested without changing the Streamlit application.
