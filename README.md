# CSUM-G: Group Software Updates for CubeSat Clusters

Authors: Ankit Gangwal, Aashish Paliwal<br>
Affiliation: CSTAR, IIIT Hyderabad<br>
Accepted at *50th IEEE Conference on Local Computer Networks (LCN 2025)*

## Overview

This repository contains the code, experiments, and data for CSUM-Group, a secure, efficient software update propagation protocol for CubeSat clusters. CSUM-Group leverages HMAC-based authentication, hashchains, and cluster-wide broadcast authentication to provide resilient, scalable software updates under realistic network conditions (latency, link failures, malicious attempts).

The implementation and experiments support the findings presented in our LCN 2025 short paper.

## Directory Structure

- `\src`
    - `CubeSat.py`: CubeSat node protocol logic (update receive/verify, broadcast, and log)
    - `GroundStatin.py`: Ground station protocol logic (hashchains, token creation, update sending)
    - `scalability_experiment.py`: Automated large-scale simulation over configurable CubeSat topologies
    - `main.py`: minimal demo

- `\csum`: Codebase for the original CSUM protocol with results (for comparison/baseline)
- `\results`: Contains all experiment outputs:
    - Each subfolder (e.g., `exp_YYYYMMDD_HHMMSS_6nodes/`) is a single simulation run, named by timestamp and node count. 
    - Each subfolder includes `experiment_data.json` (full logs, per-node stats, metrics).

- `eval_summary.py`: Aggregates experimental data, generates summary and multi-metric plots

### Requirements

Assumes Python is installed.

Install dependencies with:
```bash
pip install -r requirements.txt
```

### How to cite

Ankit Gangwal, Aashish Paliwal.<br>
**CSUM-G: Group Software Updates for CubeSat Clusters.**<br>
*In Proceedings of the 50th IEEE Conference on Local Computer Networks (IEEE LCN 2025), pp. 1-9, Sydney, Australia, October 14-16, 2025.*
