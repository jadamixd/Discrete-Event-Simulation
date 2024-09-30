import simpy
import numpy as np
import random
import matplotlib.pyplot as plt


# Parameters from the given tables
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

# Define the route structure with both eastbound and westbound travel directions
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

# Passenger Generator Process
def passenger_generator(env, bus_stop_queues):
    while True:
        stop = random.choice(list(bus_stop_queues.keys()))  # Randomly choose a bus stop
        arrival_time = env.now
        yield env.timeout(random.expovariate(ARRIVAL_RATES[stop]))  # Wait until next passenger arrives
        bus_stop_queues[stop].append(arrival_time)  # Add a passenger with arrival time to the queue
        print(f"Passenger arrived at {stop} at time {env.now}")


# Bus Entity
def bus(env, bus_stop_queues, initial_route, utilization_record):
    current_capacity = 0
    current_route = initial_route
    total_passengers_transported = 0  # Track total passengers transported over time

    while True:
        route_stops = current_route["stops"]
        route_roads = current_route["roads"]

        for i in range(len(route_stops)):
            stop = route_stops[i]
            print(f"Bus arriving at {stop} at time {env.now}")

            # Drop off passengers
            if current_capacity > 0:
                num_leaving = sum([1 for _ in range(current_capacity) if random.uniform(0, 1) < PROB_LEAVE])
                current_capacity -= num_leaving
                print(f"{num_leaving} passengers left the bus at {stop} at time {env.now}")

            # Pick up passengers
            num_waiting = len(bus_stop_queues[stop])
            num_boarding = min(num_waiting, CAPACITY - current_capacity)
            for _ in range(num_boarding):
                bus_stop_queues[stop].pop(0)
                total_passengers_transported += 1  # Count each boarding passenger as transported

            current_capacity += num_boarding
            print(f"{num_boarding} passengers boarded the bus at {stop} at time {env.now}")
            print(f"Bus capacity now: {current_capacity}/{CAPACITY}")

            # Travel to the next stop
            if i < len(route_roads):
                travel_time = TRAVEL_TIMES[route_roads[i]]
                yield env.timeout(travel_time)

        # Calculate utilization
        if total_passengers_transported > 0:
            utilization = total_passengers_transported / (CAPACITY * len(route_stops))
            utilization_record.append(utilization) 

        #End of current route: decide whether to switch routes
        print(f"Bus finished route at time {env.now}. Evaluating next route...")
        
        #Decision Logic to Switch Routes
        if current_capacity < CAPACITY * 0.5:  #bus is less than 50% full
            highest_demand_route = max(routes.values(), key=lambda r: sum(len(bus_stop_queues[stop]) for stop in r["stops"])) #choose route with highest demand (longest queue's in total)
            if highest_demand_route != current_route:
                current_route = highest_demand_route
                print(f"Switching to a new route with higher demand.")
            else:
                print(f"Continuing with the current route.")
        else:
            print(f"Continuing with the current route due to high utilization.")



def run_simulation(nb_values, num_runs):
    average_utilizations = []
    standard_errors = []

    for n_b in nb_values:
        utilization_records = []

        for _ in range(num_runs):
            env = simpy.Environment()
            bus_stop_queues = {stop: [] for route in routes.values() for stop in route["stops"]}

            # Start passenger generator
            env.process(passenger_generator(env, bus_stop_queues))

            # Start multiple buses
            utilization_record = []
            for i in range(n_b):
                route = random.choice(list(routes.values()))
                env.process(bus(env, bus_stop_queues, route, utilization_record))

            # Run simulation
            env.run(until=SIMULATION_TIME)
            utilization_records.append(np.mean(utilization_record))

        # Calculate average and standard error of utilization
        avg_utilization = np.mean(utilization_records)
        std_error = np.std(utilization_records) / np.sqrt(num_runs)

        average_utilizations.append(avg_utilization)
        standard_errors.append(std_error)

    return average_utilizations, standard_errors

# Run the simulation and plot results
nb_values = [2, 5, 7, 10, 15]
num_runs = 15
average_utilizations, standard_errors = run_simulation(nb_values, num_runs)

#Plot results
plt.figure(figsize=(10, 6))
plt.errorbar(nb_values, average_utilizations, yerr=standard_errors, fmt='o-', capsize=5, label='Average Utilization')
plt.xlabel('Number of Buses (n_b)')
plt.ylabel('Average Utilization')
plt.title('Bus Utilization vs Number of Buses')
plt.grid(True)
plt.legend()
plt.show()
