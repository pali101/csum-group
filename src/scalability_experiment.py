# scalability_experiment.py
import time, hashlib, random
import networkx as nx
from CubeSat import CubeSat
from GroundStation import GroundStation


def scalability_experiment(cubesat_counts=[5, 10, 20, 50, 100, 200, 500], updates=5):
    results = {}
    for num_cubesats in cubesat_counts:
        ground_station = GroundStation("GS")
        shared_secret = ground_station.generate_random_token(32)

        # Create one shared hashchain for all CubeSats
        hashchain = ground_station.create_hashchain(
            ground_station.generate_random_token(32), updates + 1
        )
        initial_token = hashchain[-1]
        cubesats = []
        for i in range(num_cubesats):
            cs = CubeSat(initial_token, shared_secret)
            cs.id = i  # Force CubeSat.id to match index
            cubesats.append(cs)

        # Create a connected random graph
        G = nx.erdos_renyi_graph(n=num_cubesats, p=0.2)
        while not nx.is_connected(G):
            G = nx.erdos_renyi_graph(n=num_cubesats, p=0.2)

        software_update = "Firmware update v1.3"
        total_time = 0

        for update_idx in range(updates):
            ground_station.current_token = hashchain[-(update_idx + 2)]
            ground_station.previous_token = hashchain[-(update_idx + 1)]
            transmission_token = ground_station.send_update(software_update)

            # One CubeSat receives update and stores it
            cubesats[0].receive_update(software_update, transmission_token)

            # Begin propagation from the initial CubeSat
            visited = set()
            queue = [0]
            start = time.time()

            while queue:
                next_queue = []
                for sender_id in queue:
                    sender = cubesats[sender_id]
                    for neighbor_id in G.neighbors(sender_id):
                        receiver = cubesats[neighbor_id]
                        # simulate 1-10ms dynamic delay
                        time.sleep(random.uniform(0.001, 0.010))
                        if (
                            hashlib.sha256(software_update.encode()).hexdigest()
                            in receiver.update_log
                        ):
                            continue  # Step 4: Already received

                        # Create and send token
                        update, token, sid, rid, ts = sender.broadcast_update(
                            software_update, neighbor_id
                        )

                        # Receiver verifies and may rebroadcast
                        token_func = receiver.receive_broadcast_update(
                            update, token, sid, ts
                        )
                        if token_func:
                            next_queue.append(neighbor_id)
                queue = next_queue
            # Update version
            version = 1.3 + update_idx * 0.1
            software_update = f"Firmware update v{version:.1f}"

            end = time.time()
            total_time += end - start

        avg_time_per_update = total_time / updates
        results[num_cubesats] = avg_time_per_update
        print(
            f"{num_cubesats} CubeSats: Avg propagation time: {avg_time_per_update:.6f} sec"
        )

    print("\nFinal scalability results:", results)


if __name__ == "__main__":
    scalability_experiment()
