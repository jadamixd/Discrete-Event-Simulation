import simpy
import numpy as np
import random
import matplotlib.pyplot as plt

# Parameters
CAPACITY = 20  # Capacity of the bus from Table 3
PROB_LEAVE = 0.3  # Probability a passenger leaves at a bus stop
SIMULATION_TIME = 100  # Total simulation time

# Passenger arrival rates from Table 2
ARRIVAL_RATES = {
    "S1_e": 0.3, "S1_w": 0.6,
    "S2_e": 0.1, "S2_w": 0.1,
    "S3_e": 0.3, "S3_w": 0.9,
    "S4_e": 0.2, "S4_w": 0.5,
    "S5_e": 0.6, "S5_w": 0.4,
    "S6_e": 0.6, "S6_w": 0.4,
    "S7_e": 0.6, "S7_w": 0.4
}

# Travel times from Table 1 (in minutes)
TRAVEL_TIMES = {
    "R1": 3, "R2": 7, "R3": 6,
    "R4": 1, "R5": 4, "R6": 3,
    "R7": 9, "R8": 1, "R9": 3,
    "R10": 8, "R11": 8, "R12": 5,
    "R13": 6, "R14": 2, "R15": 3
}

routes = {
    "Route_E1_E3_east": {
        "start": "E1",
        "end": "E3",
        "stops": ["S1_e", "S4_e", "S6_e"],
        "roads": ["R1", "R5", "R8", "R13"]
    },
    "Route_E1_E3_west": {
        "start": "E3",
        "end": "E1",
        "stops": ["S6_w", "S4_w", "S1_w"],
        "roads": ["R13", "R8", "R5", "R1"]
    },
    "Route_E1_E4_east": {
        "start": "E1",
        "end": "E4",
        "stops": ["S2_e", "S5_e", "S7_e"],
        "roads": ["R2", "R7", "R11", "R15"]
    },
    "Route_E1_E4_west": {
        "start": "E4",
        "end": "E1",
        "stops": ["S7_w", "S5_w", "S2_w"],
        "roads": ["R15", "R11", "R7", "R2"]
    },
    "Route_E2_E3_east": {
        "start": "E2",
        "end": "E3",
        "stops": ["S3_e", "S7_e"],
        "roads": ["R4", "R12", "R14"]
    },
    "Route_E2_E3_west": {
        "start": "E3",
        "end": "E2",
        "stops": ["S7_w", "S3_w"],
        "roads": ["R14", "R12", "R4"]
    },
    "Route_E2_E4_east": {
        "start": "E2",
        "end": "E4",
        "stops": ["S3_e", "S7_e"],
        "roads": ["R4", "R12", "R15"]
    },
    "Route_E2_E4_west": {
        "start": "E4",
        "end": "E2",
        "stops": ["S7_w", "S3_w"],
        "roads": ["R15", "R12", "R4"]
    }
}

# Passenger generator entity
def passenger_generator(env, bus_stop_queues):
    for stop in bus_stop_queues.keys():
        env.process(generate_passengers_at_stop(env, bus_stop_queues, stop))

# Helper function to generate passengers at a specific bus stop
def generate_passengers_at_stop(env, bus_stop_queues, stop):
    while True:
        interarrival_time = random.expovariate(ARRIVAL_RATES[stop])
        yield env.timeout(interarrival_time)
        arrival_time = env.now
        bus_stop_queues[stop].append(arrival_time)
        print(f"Passenger arrived at {stop} at time {env.now}")

# Bus entity with two different route switching strategies
def bus(env, bus_stop_queues, initial_route_name, utilization_record, strategy="demand_based"):
    occ = 0
    current_route_name = initial_route_name
    current_route = routes[current_route_name]

    while True:
        route_stops = current_route["stops"]
        route_roads = current_route["roads"]

        for i in range(len(route_roads)):
            travel_time = TRAVEL_TIMES[route_roads[i]]
            yield env.timeout(travel_time)

            if i < len(route_stops):
                stop = route_stops[i]
                print(f"Bus arriving at {stop} at time {env.now}")

                # Drop off passengers
                if occ > 0:
                    num_leaving = sum([1 for _ in range(occ) if random.uniform(0, 1) <= PROB_LEAVE])
                    occ -= num_leaving
                    print(f"{num_leaving} passengers left the bus at {stop} at time {env.now}")

                # Pick up passengers
                num_waiting = len(bus_stop_queues[stop])
                num_boarding = min(num_waiting, CAPACITY - occ)
                for _ in range(num_boarding):
                    bus_stop_queues[stop].pop(0)

                occ += num_boarding
                print(f"{num_boarding} passengers boarded the bus at {stop} at time {env.now}")
                print(f"Bus capacity now: {occ}/{CAPACITY}")

                # Record utilization
                utilization = occ / CAPACITY
                utilization_record.append(utilization)

        # Route switching logic based on strategy
        current_end = current_route["end"]

        if strategy == "demand_based":
            # Demand-based route switching (choose route with most waiting passengers)
            most_waiting = 0
            next_route_name = None
            possible_routes = [
                route_name for route_name, route_data in routes.items() if route_data["start"] == current_end
            ]
            for route_name in possible_routes:
                total_waiting = sum(len(bus_stop_queues[stop]) for stop in routes[route_name]["stops"])
                if total_waiting > most_waiting:
                    most_waiting = total_waiting
                    next_route_name = route_name

            if next_route_name:
                current_route_name = next_route_name
                current_route = routes[current_route_name]

        elif strategy == "random":
            # Random route switching
            possible_routes = [
                route_name for route_name, route_data in routes.items() if route_data["start"] == current_end
            ]
            if possible_routes:
                current_route_name = random.choice(possible_routes)
                current_route = routes[current_route_name]

# Running the simulation function
def run_simulation(nb_values, num_runs, strategy):
    average_utilizations = []
    standard_errors = []

    for n_b in nb_values:
        utilization_records = []

        for run in range(num_runs):
            env = simpy.Environment()
            bus_stop_queues = {stop: [] for route in routes.values() for stop in route["stops"]}

            passenger_generator(env, bus_stop_queues)

            utilization_record = []
            for i in range(n_b):
                route_name = random.choice(list(routes.keys()))
                env.process(bus(env, bus_stop_queues, route_name, utilization_record, strategy))

            env.run(until=SIMULATION_TIME)
            utilization_records.append(np.mean(utilization_record))

        avg_utilization = np.mean(utilization_records)
        std_error = np.std(utilization_records) / np.sqrt(num_runs)

        average_utilizations.append(avg_utilization)
        standard_errors.append(std_error)

    return average_utilizations, standard_errors

# Run simulations for both strategies
nb_values = [5, 7, 10, 15]
num_runs = 15

# Demand-based strategy
avg_util_demand, std_err_demand = run_simulation(nb_values, num_runs, strategy="demand_based")
plt.errorbar(nb_values, avg_util_demand, yerr=std_err_demand, fmt='o-', capsize=5, label='Demand-Based Utilization')

# Random strategy
avg_util_random, std_err_random = run_simulation(nb_values, num_runs, strategy="random")
plt.errorbar(nb_values, avg_util_random, yerr=std_err_random, fmt='o-', capsize=5, label='Random Utilization')

plt.xlabel('Number of Buses ($n_b$)')
plt.ylabel('Average Utilization')
plt.title('Bus Utilization for Different Route Selection Strategies')
plt.grid(True)
plt.legend()
plt.show()
