from datetime import datetime
import time, os, json
import numpy as np
import networkx as nx
from CubeSat import CubeSat
from GroundStation import GroundStation


def build_structured_topology(num_planes, sats_per_plane):
    G = nx.Graph()
    for plane in range(num_planes):
        for sat in range(sats_per_plane):
            node = plane * sats_per_plane + sat
            G.add_node(node)

            # Intra-plane connections (for analysis, not used in CSUM propagation)
            next_sat = (sat + 1) % sats_per_plane
            G.add_edge(node, plane * sats_per_plane + next_sat)

            # Inter-plane connections
            next_plane = (plane + 1) % num_planes
            G.add_edge(node, next_plane * sats_per_plane + sat)
    return G


MIN_DELAY_MS = 0
MAX_DELAY_MS = 24 * 60 * 60 * 1000


def simulate_updates(topology_configs=[(6, 8), (10, 10), (12, 12)], num_updates=5):
    results = {}

    for num_planes, sats_per_plane in topology_configs:
        sim_time_s = 0
        print(num_planes, sats_per_plane)
        num_sats = num_planes * sats_per_plane
        # 1) Build the graph
        G = build_structured_topology(num_planes, sats_per_plane)
        # 2) Instantiate one CubeSat per node
        gs = GroundStation("GS")
        seed = gs.generate_random_token(32)
        hashchain = gs.create_hashchain(seed, num_updates + num_sats + 10)
        initial_token = hashchain[-1]
        shared_secret = gs.generate_random_token(32)
        for n in G.nodes():
            G.nodes[n]["sat"] = CubeSat(initial_token, shared_secret)

        # Prepare experiment_data
        experiment_data = {
            "timestamp": datetime.now().isoformat(),
            "node_count": num_sats,
            "update_rounds": num_updates,
            "latency_model": "normal_15ms_std3",
            "topology_type": f"structured_{num_planes}x{sats_per_plane}",
            "edges": list(map(list, G.edges())),
            "nodes": {str(n): {"neighbors": list(G.neighbors(n))} for n in G.nodes()},
            "events": [],
            "successful_nodes_per_round": [],
        }

        sim_time_s = 0.0
        start_time = time.time()

        # 3) Run updates
        for i in range(1, num_updates + 1):
            # pick the two hashchain tokens for iteration i
            gs.current_token = hashchain[-(i + 1)]
            gs.previous_token = hashchain[-i]
            version = 1.3 + i * 0.1
            software_update = f"Firmware update v{version:.1f}"

            successes = 0
            for _, data in G.nodes(data=True):
                sat = data["sat"]
                load_delay_ms = max(0, np.random.uniform(MIN_DELAY_MS, MAX_DELAY_MS))

                # 4) simulate link‐latency
                link_latency_ms = max(0, np.random.normal(15, 3))
                total_delay_s = (link_latency_ms + load_delay_ms) / 1000.0
                sim_time_s += total_delay_s
                # sat.update_log.add((i, sim_time_s))

                # 5) send & receive
                tx_token = gs.send_update(software_update)
                sat.receive_update(software_update, tx_token)

                experiment_data["events"].append(
                    {
                        "timestamp": time.time(),
                        "sender": "GS",
                        "receiver": sat.id,
                        "latency": total_delay_s,
                        "version": f"{version:.1f}",
                    }
                )
                successes += 1

            # print(f"[t={sim_time_s}s] Finished Update {i}")
            experiment_data["successful_nodes_per_round"].append(successes)

        end_time = time.time()
        latencies = [e["latency"] for e in experiment_data["events"]]
        experiment_data.update(
            {
                "start_time": start_time,
                "end_time": end_time,
                "avg_propagation_time": np.mean(latencies),
                "max_propagation_time": np.max(latencies),
                "unreachable_percent": 100.0
                * (
                    1
                    - np.mean(
                        [
                            r / num_sats
                            for r in experiment_data["successful_nodes_per_round"]
                        ]
                    )
                ),
                "avg_retries_per_event": None,  # compute if you track retries elsewhere
                "max_retries": None,
                "packet_drop_rate": None,
                "redundant_transmissions": None,
            }
        )

        # --- Write out JSON ---
        output_dir = (
            f"results/exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{num_sats}nodes"
        )
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "experiment_data.json"), "w") as f:
            json.dump(experiment_data, f, indent=2)

        print(f"Results written to {output_dir}/experiment_data.json")


if __name__ == "__main__":
    simulate_updates(
        [
            (2, 3),
            (3, 4),
            (4, 5),
            (4, 12),
            (6, 8),
            (7, 7),
            (6, 10),
            (9, 9),
            (10, 10),
            (11, 11),
            (15, 15),
            (20, 20),
            (25, 20),
            (30, 20),
        ]
    )
