import time, hashlib, random
import networkx as nx
from CubeSat import CubeSat
from GroundStation import GroundStation

import json
import os
from datetime import datetime


def scalability_experiment(cubesat_counts=[5, 10, 20, 50, 100], updates=5):
    results = {}
    for num_cubesats in cubesat_counts:
        experiment_data = {
            "timestamp": datetime.now().isoformat(),
            "node_count": num_cubesats,
            "update_rounds": updates,
            "latency_model": "random_1_10ms_with_10_percent_packet_drop",
            "topology_type": "erdos_renyi_connected",
            "edges": [],
            "nodes": {},
            "events": [],
            "successful_nodes_per_round": [],
        }
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
        experiment_data["edges"] = list(G.edges())
        for node in G.nodes():
            experiment_data["nodes"][node] = {
                "neighbors": list(G.neighbors(node)),
                "update_history": [],
            }

        software_update = "Firmware update v1.3"
        total_time = 0
        version = 1.3

        for update_idx in range(updates):
            # Reset per-update state
            for node_id in experiment_data["nodes"]:
                experiment_data["nodes"][node_id]["update_history"].append(
                    {"received": False, "time_received": None, "hops": None}
                )

            ground_station.current_token = hashchain[-(update_idx + 2)]
            ground_station.previous_token = hashchain[-(update_idx + 1)]
            transmission_token = ground_station.send_update(software_update)

            # Step 1 & 2: One CubeSat receives update and stores it
            cubesats[0].receive_update(software_update, transmission_token)

            # Step 3 to 5: Begin propagation from the initial CubeSat
            visited = set()
            queue = [0]
            start = time.time()
            experiment_data["start_time"] = start

            while queue:
                next_queue = []
                for sender_id in queue:
                    sender = cubesats[sender_id]
                    for neighbor_id in G.neighbors(sender_id):
                        receiver = cubesats[neighbor_id]

                        latency = random.uniform(0.001, 0.010)
                        time.sleep(latency)  # Simulate 1-10ms dynamic latency

                        if (
                            hashlib.sha256(software_update.encode()).hexdigest()
                            in receiver.update_log
                        ):
                            continue  # Step 4: Already received

                        # Step 3: Create and send token
                        update, token, sid, rid, ts = sender.broadcast_update(
                            software_update, neighbor_id
                        )

                        # Step 5: Receiver verifies and may rebroadcast
                        # Simulate packet drop with 10% probability
                        if random.random() < 0.1:
                            token_func = None  # packet dropped
                        else:
                            token_func = receiver.receive_broadcast_update(
                                update, token, sid, ts
                            )

                        experiment_data["events"].append(
                            {
                                "timestamp": time.time(),
                                "sender": sender_id,
                                "receiver": neighbor_id,
                                "latency": latency,
                                "token_valid": token_func is not None,
                                "version": f"{version:.1f}",
                            }
                        )

                        if token_func:
                            sender_hops = experiment_data["nodes"][sender_id][
                                "update_history"
                            ][-1]["hops"]
                            experiment_data["nodes"][neighbor_id]["update_history"][
                                -1
                            ] = {
                                "received": True,
                                "time_received": time.time() - start,
                                "hops": (
                                    (sender_hops + 1) if sender_hops is not None else 1
                                ),
                            }
                            next_queue.append(neighbor_id)
                queue = next_queue

            successful_nodes_this_round = sum(
                1
                for node in experiment_data["nodes"].values()
                if node["update_history"][-1]["received"]
            )
            experiment_data["successful_nodes_per_round"].append(
                successful_nodes_this_round
            )

            # Update version
            version = 1.3 + update_idx * 0.1
            software_update = f"Firmware update v{version:.1f}"

            end = time.time()
            total_time += end - start

        avg_time_per_update = total_time / updates
        results[num_cubesats] = avg_time_per_update
        experiment_data["avg_propagation_time"] = avg_time_per_update

        output_dir = f"results/exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{num_cubesats}nodes"
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "experiment_data.json"), "w") as f:
            json.dump(experiment_data, f, indent=2)

        print(
            f"{num_cubesats} CubeSats: Avg propagation time: {avg_time_per_update:.6f} sec. Data saved to {output_dir}"
        )

    print("Final scalability results:", results)


if __name__ == "__main__":
    scalability_experiment()
