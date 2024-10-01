import simpy
import numpy as np
import random
import matplotlib.pyplot as plt

# Parameters
CAPACITY = 20  # Capacity of the bus from Table 3
PROB_LEAVE = 0.3  # Probability a passenger leaves at a bus stop
SIMULATION_TIME = 100  # Increased total simulation time

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
        "stops": ["S1_e", "S4_e", "S6_e"],
        "roads": ["R1", "R5", "R8", "R13"]
    },
    "Route_E1_E3_west": {
        "stops": ["S1_w", "S4_w", "S6_w"],
        "roads": ["R1", "R5", "R8", "R13"]
    },
    "Route_E1_E4_east": {
        "stops": ["S2_e", "S5_e", "S7_e"],
        "roads": ["R2", "R7", "R11", "R15"]
    },
    "Route_E1_E4_west": {
        "stops": ["S2_w", "S5_w", "S7_w"],
        "roads": ["R2", "R7", "R11", "R15"]
    },
    "Route_E2_E3_east": {
        "stops": ["S3_e", "S7_e"],
        "roads": ["R4", "R12", "R14"]
    },
    "Route_E2_E3_west": {
        "stops": ["S3_w", "S7_w"],
        "roads": ["R4", "R12", "R14"]
    },
    "Route_E2_E4_east": {
        "stops": ["S3_e", "S7_e"],
        "roads": ["R4", "R12", "R15"]
    },
    "Route_E2_E4_west": {
        "stops": ["S3_w", "S7_w"],
        "roads": ["R4", "R12", "R15"]
    }
}

class Passenger:
    def __init__(self, env, passenger_id, arrival_time, destination):
        self.env = env
        self.passenger_id = passenger_id
        self.arrival_time = arrival_time
        self.destination = destination
        self.boarding_time = None
        self.total_travel_time = None

# Passenger generator
def passenger_generator(env, bus_stop_queues, passenger_list):
    passenger_id = 0
    while True:
        stop = random.choice(list(bus_stop_queues.keys()))
        arrival_time = env.now
        destination = random.choice([s for s in bus_stop_queues.keys() if s != stop])  # Ensure destination is different

        # Create new passenger entity
        passenger = Passenger(env, passenger_id, arrival_time, destination)
        passenger_id += 1

        # Add passenger to bus stop queue
        bus_stop_queues[stop].append(passenger)
        passenger_list.append(passenger)

        print(f"Passenger {passenger.passenger_id} arrived at {stop} at time {env.now}")

        yield env.timeout(random.expovariate(ARRIVAL_RATES[stop]))

# Bus entity with dynamic route selection
def bus(env, bus_stop_queues, initial_route_name, utilization_record):
    current_capacity = 0
    current_route_name = initial_route_name
    current_route = routes[current_route_name]
    passengers_on_board = []

    while True:
        route_stops = current_route["stops"]
        route_roads = current_route["roads"]

        for i in range(len(route_stops)):
            stop = route_stops[i]
            print(f"Bus arriving at {stop} at time {env.now}")

            # Drop off passengers at their destination stop
            passengers_to_leave = [p for p in passengers_on_board if p.destination == stop]
            for passenger in passengers_to_leave:
                passengers_on_board.remove(passenger)
                current_capacity -= 1
                passenger.total_travel_time = env.now - passenger.boarding_time
                print(f"Passenger {passenger.passenger_id} left the bus at {stop} at time {env.now}")

            # Pick up passengers waiting at the stop
            num_waiting = len(bus_stop_queues[stop])
            if num_waiting > 0:
                print(f"{num_waiting} passengers waiting at {stop} at time {env.now}")

            num_boarding = min(num_waiting, CAPACITY - current_capacity)
            for _ in range(num_boarding):
                passenger = bus_stop_queues[stop].pop(0)
                passenger.boarding_time = env.now
                passengers_on_board.append(passenger)
                current_capacity += 1
                print(f"Passenger {passenger.passenger_id} boarded the bus at {stop} at time {env.now}")

            print(f"Bus capacity now: {current_capacity}/{CAPACITY}")

            # Record utilization at each stop and road segment
            utilization = current_capacity / CAPACITY  # Calculate utilization as current capacity divided by max capacity
            utilization_record.append(utilization)

            # Travel to the next stop
            if i < len(route_roads):
                travel_time = TRAVEL_TIMES[route_roads[i]]
                yield env.timeout(travel_time)

        # Choose a new route randomly after finishing the current route
        current_route_name = random.choice(list(routes.keys()))
        current_route = routes[current_route_name]
        print(f"Bus switching to a new route: {current_route_name} at time {env.now}")


# Function to run multiple simulations and collect data for different numbers of buses
def run_simulation(nb_values, num_runs):
    average_utilizations = []
    standard_errors = []

    for n_b in nb_values:
        utilization_records = []

        for _ in range(num_runs):
            env = simpy.Environment()
            bus_stop_queues = {stop: [] for route in routes.values() for stop in route["stops"]}
            passenger_list = []

            env.process(passenger_generator(env, bus_stop_queues, passenger_list))

            # Start multiple buses
            utilization_record = []
            for i in range(n_b):
                route = random.choice(list(routes.keys()))  # Select random initial route for each bus
                env.process(bus(env, bus_stop_queues, route, utilization_record))

            # Run the simulation
            env.run(until=SIMULATION_TIME)
            utilization_records.append(np.mean(utilization_record))

        # Calculate average utilization and standard error
        avg_utilization = np.mean(utilization_records)
        std_error = np.std(utilization_records) / np.sqrt(num_runs)

        average_utilizations.append(avg_utilization)
        standard_errors.append(std_error)

    return average_utilizations, standard_errors

# Run the simulation with different numbers of buses and plot results
nb_values = [5, 7, 10, 15]
num_runs = 15
average_utilizations, standard_errors = run_simulation(nb_values, num_runs)

# Plot results
plt.figure(figsize=(10, 6))
plt.errorbar(nb_values, average_utilizations, yerr=standard_errors, fmt='o-', capsize=5, label='Average Utilization')
plt.xlabel('Number of Buses ($n_b$)')
plt.ylabel('Average Utilization')
plt.title('Bus Utilization vs Number of Buses')
plt.grid(True)
plt.legend()
plt.show()