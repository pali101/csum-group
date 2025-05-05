from collections import defaultdict
import os, json
import pandas as pd

extended_rows = []
results_dir = "results"

for folder in os.listdir(results_dir):
    folder_path = os.path.join(results_dir, folder)
    json_file = os.path.join(folder_path, "experiment_data.json")
    if os.path.isfile(json_file):
        with open(json_file, "r") as f:
            data = json.load(f)

        topology = data.get("topology_type")
        nodes = data.get("node_count")
        edges = len(data.get("edges", [])) - len(data.get("disabled_edges", []))
        avg_time = round(data.get("avg_propagation_time", 0), 2)

        # Max hops
        max_hops = 0
        received_nodes = 0
        total_hops = 0
        for node in data.get("nodes", {}).values():
            hist = node.get("update_history", [])
            if hist:
                hop = hist[-1].get("hops")
                if hop is not None:
                    max_hops = max(max_hops, hop)
                    total_hops += hop
                    received_nodes += 1

        # Retry stats
        retries = [e["retry"] for e in data["events"]]
        avg_retries = sum(retries) / len(retries) if retries else 0

        # Redundant messages
        from collections import Counter

        target_counts = Counter((e["receiver"], e["version"]) for e in data["events"])
        redundant_attempts = sum(
            1 for (_, v), count in target_counts.items() if count > 1
        )

        # Malicious token count
        malicious_count = sum(1 for e in data["events"] if e.get("possibly_malicious"))

        # Packet drop estimate (token_valid = false and not malicious)
        failed_token_attempts = sum(
            1
            for e in data["events"]
            if not e["token_valid"] and not e.get("possibly_malicious")
        )

        success_rate = 100 - data.get("unreachable_percent", 0)

        extended_rows.append(
            {
                "Topology": topology,
                "Nodes": nodes,
                "Edges": edges,
                "Average Time (s)": avg_time,
                "Max Hops": max_hops,
                "Success Rate (%)": round(success_rate),
                "Average Retries": round(avg_retries, 2),
                "Max Propagation Time (s)": round(
                    data.get("max_propagation_time", 0), 3
                ),
                "Redundant Messages": redundant_attempts,
                "Malicious Tokens": malicious_count,
                "Failed Token Attempts": failed_token_attempts,
                "Average Degree": round(data.get("avg_node_degree", 0), 2),
                "Diameter": data.get("graph_diameter"),
                "Isolated Nodes": data.get("num_isolated", 0),
            }
        )

extended_df = pd.DataFrame(extended_rows)
extended_df["Config"] = extended_df["Topology"].str.replace("structured_", "")
extended_df.drop(columns=["Topology"], inplace=True)
extended_df.sort_values(by="Nodes", inplace=True)

print(extended_df.to_string(index=False))
extended_df.to_csv("experiment_summary.csv", index=False)

import matplotlib.pyplot as plt

# extended_df.plot(x="Nodes", y="Avg Time (s)", kind="line", marker="o")
# plt.title("Average Propagation Time vs. Number of Nodes")
# plt.grid(True)
# plt.savefig("propagation_vs_nodes.png")
fig, axs = plt.subplots(2, 3, figsize=(18, 10))
# fig.suptitle("CubeSat Software Update Metrics vs. Node Count", fontsize=20)

metrics = [
    ("Average Time (s)", "Average Propagation Time"),
    ("Max Hops", "Maximum Hops"),
    ("Average Retries", "Average Retries per Event"),
    ("Redundant Messages", "Redundant Messages"),
    ("Failed Token Attempts", "Failed Token Attempts"),
    ("Malicious Tokens", "Malicious Tokens Detected"),
]


# Plot each metric
for ax, (col, title) in zip(axs.flatten(), metrics):
    ax.plot(extended_df["Nodes"], extended_df[col])
    ax.set_title(title, fontsize=26)
    ax.set_xlabel("Number of Nodes", fontsize=20)
    ax.set_ylabel(col, fontsize=20)
    ax.tick_params(axis="both", labelsize=18)
    ax.grid(True)

# Hide unused subplots if any
for i in range(len(metrics), len(axs.flatten())):
    axs.flatten()[i].axis("off")

plt.tight_layout(rect=[0, 0.03, 1, 0.93], h_pad=3.0)
plt.savefig("combined_metrics.pdf")
