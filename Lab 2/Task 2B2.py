import simpy
import numpy as np
import random
import matplotlib.pyplot as plt

#Parameters
CAPACITY = 20  #Capacity of the bus
PROB_LEAVE = 0.3 #Probability a passenger leaves at a bus stop
SIMULATION_TIME = 100  #Simulation time

#Arrival rates for each bus stop
ARRIVAL_RATES = {
    "S1_e": 0.3, "S1_w": 0.6,
    "S2_e": 0.1, "S2_w": 0.1,
    "S3_e": 0.3, "S3_w": 0.9,
    "S4_e": 0.2, "S4_w": 0.5,
    "S5_e": 0.6, "S5_w": 0.4,
    "S6_e": 0.6, "S6_w": 0.4,
    "S7_e": 0.6, "S7_w": 0.4
}

#Travel times for each road segment
TRAVEL_TIMES = {
    "R1": 3, "R2": 7, "R3": 6,
    "R4": 1, "R5": 4, "R6": 3,
    "R7": 9, "R8": 1, "R9": 3,
    "R10": 8, "R11": 8, "R12": 5,
    "R13": 6, "R14": 2, "R15": 3
}

#Routes from Lab 1
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

#Passenger entity
class Passenger:
    def __init__(self, env, passenger_id, arrival_time, destination):
        self.env = env
        self.passenger_id = passenger_id
        self.arrival_time = arrival_time
        self.destination = destination
        self.boarding_time = None
        self.total_travel_time = None

#Passenger generator entity
def passenger_generator(env, stop, bus_stop_queues, passenger_list):
    passenger_id = 0
    while True:
        interarrival_time = random.expovariate(ARRIVAL_RATES[stop])
        yield env.timeout(interarrival_time)  #Wait until next passenger arrives

        #Create a new passenger
        arrival_time = env.now
        destination = random.choice([s for s in bus_stop_queues.keys() if s != stop])  #Ensure the destination is different from the current stop
        passenger = Passenger(env, passenger_id, arrival_time, destination)
        passenger_id += 1

        #Add passenger to the bus stop queue
        bus_stop_queues[stop].append(passenger)
        passenger_list.append(passenger)

#Bus entity
def bus(env, bus_stop_queues, initial_route_name, utilization_record, travel_times, strategy):
    occ = 0
    current_route_name = initial_route_name
    current_route = routes[current_route_name]
    passengers_on_board = []

    while True:
        route_stops = current_route["stops"]
        route_roads = current_route["roads"]

        #Iterate over the roads and stops
        for i in range(len(route_roads)):
            #Travel time for the road segment leading up to the next stop
            travel_time = TRAVEL_TIMES[route_roads[i]]
            yield env.timeout(travel_time)
            
            #Stop operations if there is a corresponding stop for the current road
            if i < len(route_stops):
                stop = route_stops[i]

                #Drop off passengers at their destination stop
                passengers_to_leave = [p for p in passengers_on_board if random.uniform(0, 1) <= PROB_LEAVE]
                for passenger in passengers_to_leave:
                    passengers_on_board.remove(passenger)
                    occ -= 1
                    passenger.total_travel_time = env.now - passenger.boarding_time
                    travel_times.append(passenger.total_travel_time)

                #Pick up passengers waiting at the stop
                num_waiting = len(bus_stop_queues[stop])
                num_boarding = min(num_waiting, CAPACITY - occ)
                for _ in range(num_boarding):
                    passenger = bus_stop_queues[stop].pop(0)
                    passenger.boarding_time = env.now
                    passengers_on_board.append(passenger)
                    occ += 1

                #Utilization calculations
                utilization = occ / CAPACITY
                utilization_record.append(utilization)

        """"""""""""""""""""""
        Route switching logic
        """""""""""""""""""""""
        #Determine the next route dynamically based on the current route's end
        current_end = current_route["end"]

        if strategy == "demand":
            #Demand-based route selection
            most_waiting = 0
            next_route_name = None

            #Find all possible routes that start from the current end stop
            possible_routes = [
                route_name for route_name, route_data in routes.items() if route_data["start"] == current_end
            ]

            #Iterate over all possible routes and find the one with the most passengers waiting at all stops
            for route_name in possible_routes:
                total_waiting = sum(len(bus_stop_queues[stop]) for stop in routes[route_name]["stops"])  #Calculate total waiting passengers at all stops on the route
                
                if total_waiting > most_waiting:
                    most_waiting = total_waiting
                    next_route_name = route_name
        else:
            #Random route selection strategy
            possible_routes = [
                route_name for route_name, route_data in routes.items() if route_data["start"] == current_end
            ]
            next_route_name = random.choice(possible_routes) if possible_routes else None

        #Update the current route to the one chosen by the strategy
        if next_route_name:
            current_route_name = next_route_name
            current_route = routes[current_route_name]
            

#Function to run simulations and log results
def run_simulation(nb_values, num_runs, strategy):
    average_utilizations = []
    average_travel_times = []

    for n_b in nb_values:
        utilization_records = []
        travel_times = []

        for run in range(num_runs):
            env = simpy.Environment()
            bus_stop_queues = {stop: [] for route in routes.values() for stop in route["stops"]}
            passenger_list = []

            #Start a passenger generator process for each bus stop
            for stop in bus_stop_queues.keys():
                env.process(passenger_generator(env, stop, bus_stop_queues, passenger_list))

            #Start multiple buses
            utilization_record = []
            for i in range(n_b):
                route = random.choice(list(routes.keys()))  #Select random start route for each bus
                env.process(bus(env, bus_stop_queues, route, utilization_record, travel_times, strategy))

            #Run the simulation
            env.run(until=SIMULATION_TIME)
            utilization_records.append(np.mean(utilization_record))

        #Calculate average utilization
        avg_utilization = np.mean(utilization_records)
        average_utilizations.append(avg_utilization)

        #Calculate average travel time
        avg_travel_time = np.mean(travel_times) if len(travel_times) > 0 else 0
        average_travel_times.append(avg_travel_time)

    return average_utilizations, average_travel_times

nb_values = [5, 7, 10, 15]
num_runs = 15
strategies = ["demand", "random"]
results = {}

for strategy in strategies:
    avg_utilizations, avg_travel_times = run_simulation(nb_values, num_runs, strategy)
    results[strategy] = (avg_utilizations, avg_travel_times)

#Plotting average utilization for both strategies
plt.figure(figsize=(10, 6))
for strategy, (avg_utilizations, avg_travel_times) in results.items():
    plt.plot(nb_values, avg_utilizations, marker='o', linestyle='-', label=f'{strategy.capitalize()} Utilization')

plt.xlabel('Number of Buses ($n_b$)')
plt.ylabel('Average Utilization')
plt.title('Bus Utilization for Different Route Selection Strategies')
plt.grid(True)
plt.legend()
plt.show()

#Plotting average travel time for both strategies
plt.figure(figsize=(10, 6))
for strategy, (avg_utilizations, avg_travel_times) in results.items():
    plt.plot(nb_values, avg_travel_times, marker='o', linestyle='-', label=f'{strategy.capitalize()} Travel Time')

plt.xlabel('Number of Buses ($n_b$)')
plt.ylabel('Average Travel Time')
plt.title('Average Travel Time for Different Route Selection Strategies')
plt.grid(True)
plt.legend()
plt.show()
