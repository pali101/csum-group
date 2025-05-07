from collections import defaultdict, Counter
import os, json
import pandas as pd
import matplotlib.pyplot as plt

# Initialize data collection
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
        edges = len(data.get("edges", []))
        avg_time = round(data.get("avg_propagation_time", 0), 2)
        max_time = round(data.get("max_propagation_time", 0), 2)

        # Retry stats
        retries = [e.get("retry", 0) for e in data["events"] if "retry" in e]
        avg_retries = sum(retries) / len(retries) if retries else 0

        # Redundant messages
        target_counts = Counter((e["receiver"], e["version"]) for e in data["events"])
        redundant_attempts = sum(
            count - 1 for count in target_counts.values() if count > 1
        )

        # Malicious token count (not available in provided data, assumed 0)
        malicious_count = sum(1 for e in data["events"] if e.get("possibly_malicious"))

        # Failed token attempts (token_valid = false and not malicious)
        failed_token_attempts = sum(
            1
            for e in data["events"]
            if not e.get("token_valid", True) and not e.get("possibly_malicious")
        )

        success_rate = 100 - data.get("unreachable_percent", 0)

        avg_degree = round(
            sum(len(node["neighbors"]) for node in data["nodes"].values()) / nodes, 2
        )

        extended_rows.append(
            {
                "Topology": topology,
                "Nodes": nodes,
                "Edges": edges,
                "Average Time (s)": avg_time,
                "Max Time (s)": max_time,
                "Malicious Tokens": malicious_count,
                "Failed Token Attempts": failed_token_attempts,
                "Average Degree": avg_degree,
            }
        )

extended_df = pd.DataFrame(extended_rows)
extended_df["Config"] = extended_df["Topology"].str.replace("structured_", "")
extended_df.drop(columns=["Topology"], inplace=True)
extended_df.sort_values(by="Nodes", inplace=True)

# Display the DataFrame
print(extended_df.to_string(index=False))
extended_df.to_csv("experiment_summary.csv", index=False)

# Plotting
fig, axs = plt.subplots(2, 3, figsize=(18, 10))

metrics = [
    ("Average Time (s)", "Average Propagation Time"),
    ("Max Time (s)", "Maximum Propagation Time"),
    ("Failed Token Attempts", "Failed Token Attempts"),
    ("Malicious Tokens", "Malicious Tokens Detected"),
]

for ax, (col, title) in zip(axs.flatten(), metrics):
    ax.plot(extended_df["Nodes"], extended_df[col], marker="o")
    ax.set_title(title, fontsize=18)
    ax.set_xlabel("Number of Nodes", fontsize=16)
    ax.set_ylabel(col, fontsize=16)
    ax.tick_params(axis="both", labelsize=14)
    ax.grid(True)

for i in range(len(metrics), len(axs.flatten())):
    axs.flatten()[i].axis("off")

plt.tight_layout(rect=[0, 0.03, 1, 0.93], h_pad=3.0)
# plt.savefig("combined_metrics.pdf")
