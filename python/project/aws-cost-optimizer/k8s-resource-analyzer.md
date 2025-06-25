# Kubernetes Resource Analyzer

## Overview
A comprehensive tool for analyzing and monitoring resource usage in Kubernetes clusters. Provides detailed insights into CPU and memory utilization at node, pod, and namespace levels.

## Features

- Node-level resource analysis (CPU/Memory)
- Pod-level resource tracking with filtering
- Namespace-level resource aggregation
- Multiple output formats (text, CSV, JSON, tree)
- Sorting by CPU or memory usage
- Comprehensive filtering capabilities

## Installation

1. Ensure Python 3.6+ is installed
2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your kubeconfig:
```bash
export KUBECONFIG=/path/to/your/kubeconfig
```

## Usage

### Basic Commands

```bash
# Show cluster-wide resource usage (nodes and namespaces)
python k8s_resource_analyzer.py

# Analyze specific namespace(s)
python k8s_resource_analyzer.py -n namespace1,namespace2

# Filter by pod name(s)
python k8s_resource_analyzer.py -p pod-name1,pod-name2

# Sort output by CPU or memory
python k8s_resource_analyzer.py --sort cpu
python k8s_resource_analyzer.py --sort mem

# Change output format
python k8s_resource_analyzer.py --output json
python k8s_resource_analyzer.py --output csv
```

### Options

| Option | Description |
|--------|-------------|
| `-n, --namespace` | Analyze specific namespace(s) (comma-separated) |
| `-p, --pods` | Filter by pod name(s) (comma-separated) |
| `-s, --sort` | Sort by `cpu` or `mem` (memory) |
| `-o, --output` | Output format: `text`, `csv`, `json`, or `tree` |
| `-h, --help` | Show help message |

## Output Examples

### Node Analysis
```
NODE_NAME              CPU_USED/TOTAL  %AGE_CPU_USAGE  MEM_USED/TOTAL(GB)  %AGE_MEM_USAGE
node1 [master]         1200m/4000m     ████30%        4.2/16 GB           ████26%
node2 [worker]         2400m/8000m     ████30%        8.4/32 GB           ████26%
```

### Namespace Analysis
```
NAMESPACE     CPU_USED  %AGE_NS_TOTAL_CPU  MEMORY_USED(GB)  %AGE_NS_TOTAL_MEM
default       800m      ████20%            2.1 GB           ████15%
kube-system   1200m     ████30%            3.5 GB           ████25%
```

## Requirements

- Kubernetes cluster with metrics-server installed
- Python 3.6+
- Kubernetes Python client
- Proper RBAC permissions for the kubeconfig user

## Screenshots
![alt text](<Screenshot 2025-06-25 at 4.06.09 PM.png>) ![alt text](<Screenshot 2025-06-25 at 4.06.17 PM.png>)

## License
Apache License 2.0
```