import time, hashlib, random
import networkx as nx
from CubeSat import CubeSat
from GroundStation import GroundStation

import json
import os
from datetime import datetime
from collections import Counter


def build_structured_topology(num_planes, sats_per_plane):
    G = nx.Graph()
    for plane in range(num_planes):
        for sat in range(sats_per_plane):
            node = plane * sats_per_plane + sat
            G.add_node(node)

            # Intra-plane connections (ring)
            next_sat = (sat + 1) % sats_per_plane
            G.add_edge(node, plane * sats_per_plane + next_sat)

            # Inter-plane connections
            next_plane = (plane + 1) % num_planes
            G.add_edge(node, next_plane * sats_per_plane + sat)
    return G


def scalability_experiment(topology_configs=[(6, 8), (10, 10), (12, 12)], updates=5):
    results = {}
    for num_planes, sats_per_plane in topology_configs:
        num_cubesats = num_planes * sats_per_plane
        print(
            f"\nRunning experiment for {num_planes}x{sats_per_plane} = {num_cubesats} CubeSats"
        )
        experiment_data = {
            "timestamp": datetime.now().isoformat(),
            "node_count": num_cubesats,
            "update_rounds": updates,
            "latency_model": "normal_5ms_std1_with_10_percent_link_failure_and_packet_drop",
            "topology_type": f"structured_{num_planes}x{sats_per_plane}",
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

        # Create a  graph
        G = build_structured_topology(num_planes, sats_per_plane)
        total_edges = list(G.edges())
        num_to_remove = int(len(total_edges) * 0.1)
        failed_links = random.sample(total_edges, num_to_remove)
        G.remove_edges_from(failed_links)
        experiment_data["disabled_edges"] = failed_links
        experiment_data["edges"] = list(G.edges())

        experiment_data["avg_node_degree"] = (
            sum(dict(G.degree()).values()) / G.number_of_nodes()
        )
        experiment_data["graph_diameter"] = (
            nx.diameter(G) if nx.is_connected(G) else None
        )
        experiment_data["isolated_nodes"] = [n for n, d in G.degree() if d == 0]
        experiment_data["num_isolated"] = len(experiment_data["isolated_nodes"])
        experiment_data["is_connected"] = nx.is_connected(G)
        for node in G.nodes():
            experiment_data["nodes"][node] = {
                "neighbors": list(G.neighbors(node)),
                "update_history": [],
            }

        total_time = 0

        for update_idx in range(updates):
            # Set version and software update string BEFORE sending
            version = 1.3 + update_idx * 0.1
            software_update = f"Firmware update v{version:.1f}"
            max_retries = 3
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
                        retry_count = 0
                        token_func = None

                        while retry_count < max_retries:
                            latency = max(0, random.normalvariate(0.005, 0.001))
                            time.sleep(latency)  # Simulate 1-10ms dynamic latency

                            # Simulate malicious token with 5 percent probability
                            is_possibly_malicious = (
                                random.random() < 0.05 and retry_count == 0
                            )
                            if is_possibly_malicious:
                                fake_token = hashlib.sha256(
                                    str(random.random()).encode()
                                ).hexdigest()
                                token_func = receiver.receive_broadcast_update(
                                    update, fake_token, sid, ts
                                )
                            # Simulate packet drop with 10% probability
                            elif random.random() < 0.1:
                                token_func = None  # packet dropped
                            else:
                                token_func = receiver.receive_broadcast_update(
                                    update, token, sid, ts
                                )
                            # Log each attempt
                            experiment_data["events"].append(
                                {
                                    "timestamp": time.time(),
                                    "sender": sender_id,
                                    "receiver": neighbor_id,
                                    "latency": latency,
                                    "token_valid": token_func is not None,
                                    "version": f"{version:.1f}",
                                    "retry": retry_count,
                                    "possibly_malicious": is_possibly_malicious,
                                }
                            )

                            if token_func:
                                break
                            retry_count += 1

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

            end = time.time()
            total_time += end - start

        avg_time_per_update = total_time / updates
        results[num_cubesats] = avg_time_per_update
        experiment_data["avg_propagation_time"] = avg_time_per_update

        # Unreachable nodes (%)
        total_nodes = len(experiment_data["nodes"])
        unreachable = sum(
            1
            for node in experiment_data["nodes"].values()
            if not node["update_history"][-1]["received"]
        )
        experiment_data["unreachable_percent"] = 100 * unreachable / total_nodes

        # Retry stats
        retries = [e["retry"] for e in experiment_data["events"]]
        experiment_data["avg_retries_per_event"] = (
            sum(retries) / len(retries) if retries else 0
        )
        experiment_data["max_retries"] = max(retries) if retries else 0

        # Packet drop rate
        drops = sum(1 for e in experiment_data["events"] if not e["token_valid"])
        experiment_data["packet_drop_rate"] = (
            100 * drops / len(experiment_data["events"])
            if experiment_data["events"]
            else 0
        )

        # Redundancy rate

        target_counts = Counter(
            (e["receiver"], e["version"]) for e in experiment_data["events"]
        )
        redundant_attempts = sum(
            1 for (_, v), count in target_counts.items() if count > 1
        )
        experiment_data["redundant_transmissions"] = redundant_attempts

        # Max propagation time
        times = [
            h["time_received"]
            for node in experiment_data["nodes"].values()
            for h in node["update_history"]
            if h["time_received"] is not None
        ]
        experiment_data["max_propagation_time"] = max(times) if times else 0

        output_dir = f"results/exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{num_cubesats}nodes"
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "experiment_data.json"), "w") as f:
            json.dump(experiment_data, f, indent=2)

        print(
            f"{num_cubesats} CubeSats: Avg propagation time: {avg_time_per_update:.6f} sec. Data saved to {output_dir}"
        )

    print("Final scalability results:", results)


if __name__ == "__main__":
    scalability_experiment(
        [(2, 3), (3, 4), (4, 5), (6, 8), (10, 10), (12, 12), (15, 15)]
    )
