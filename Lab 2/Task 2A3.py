import simpy
import random

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

# Define the route structure as in Section II.A.2
routes = {
    "Route_E1_E3": {
        "stops": ["S1_e", "S2_e", "S3_e"],
        "roads": ["R1", "R2", "R3"]
    },
    "Route_E1_E4": {
        "stops": ["S1_w", "S4_w", "S5_w"],
        "roads": ["R4", "R5", "R6"]
    },
    "Route_E2_E3": {
        "stops": ["S2_e", "S3_e"],
        "roads": ["R7", "R8"]
    },
    "Route_E2_E4": {
        "stops": ["S2_w", "S4_w"],
        "roads": ["R9", "R10"]
    }
}

# Passenger Generator Process
def passenger_generator(env, bus_stop_queues):
    """Generate passengers at each bus stop at an exponential rate."""
    while True:
        stop = random.choice(list(bus_stop_queues.keys()))  # Randomly choose a bus stop
        yield env.timeout(random.expovariate(ARRIVAL_RATES[stop]))  # Wait until next passenger arrives
        bus_stop_queues[stop].append(1)  # Add a passenger to the queue
        print(f"Passenger arrived at {stop} at time {env.now}")

# Bus Process
def bus(env, bus_stop_queues, route):
    """Simulate a bus moving through a set of stops, picking up and dropping off passengers."""
    current_capacity = 0  # Number of passengers on the bus initially
    route_stops = route["stops"]

    while True:
        for stop in route_stops:
            print(f"Bus arriving at {stop} at time {env.now}")
            yield env.timeout(2)  # Simulate stopping time at the stop (2 minutes per stop)

            # Drop off passengers based on probability
            if current_capacity > 0:
                num_leaving = sum([1 for _ in range(current_capacity) if random.uniform(0, 1) < PROB_LEAVE])
                current_capacity -= num_leaving
                print(f"{num_leaving} passengers left the bus at {stop} at time {env.now}")

            # Pick up passengers up to remaining capacity
            num_waiting = len(bus_stop_queues[stop])
            num_boarding = min(num_waiting, CAPACITY - current_capacity)
            current_capacity += num_boarding

            # Remove the boarded passengers from the queue
            bus_stop_queues[stop] = bus_stop_queues[stop][num_boarding:]

            print(f"{num_boarding} passengers boarded the bus at {stop} at time {env.now}")
            print(f"Bus capacity now: {current_capacity}/{CAPACITY}")

            # Log current bus capacity
            print(f"CAP - Rest at {stop}: {CAPACITY - current_capacity}")

        # Continue looping over the route until the simulation ends

# Environment Setup
env = simpy.Environment()

# Define bus stops and create queues for each stop from all defined routes
bus_stop_queues = {stop: [] for route in routes.values() for stop in route["stops"]}

# Start the processes for all four routes
env.process(passenger_generator(env, bus_stop_queues))

# Adding multiple buses for each route
env.process(bus(env, bus_stop_queues, routes["Route_E1_E3"]))  # Bus for Route_E1_E3
env.process(bus(env, bus_stop_queues, routes["Route_E1_E4"]))  # Bus for Route_E1_E4
env.process(bus(env, bus_stop_queues, routes["Route_E2_E3"]))  # Bus for Route_E2_E3
env.process(bus(env, bus_stop_queues, routes["Route_E2_E4"]))  # Bus for Route_E2_E4

# Run the simulation
env.run(until=SIMULATION_TIME)
