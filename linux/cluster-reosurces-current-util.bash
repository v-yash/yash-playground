#!/bin/bash

# Get resource definitions (requests/limits) for deployments and statefulsets
kubectl get deployments,statefulsets -n default \
  -o custom-columns="APP:.metadata.name,CPU_REQUEST:.spec.template.spec.containers[*].resources.requests.cpu,MEMORY_REQUEST:.spec.template.spec.containers[*].resources.requests.memory,CPU_LIMIT:.spec.template.spec.containers[*].resources.limits.cpu,MEMORY_LIMIT:.spec.template.spec.containers[*].resources.limits.memory" | sort -k1 > resources.txt

# Get current utilization from kubectl top pods
kubectl top pods -n default --no-headers | awk '{print $1, $2, $3}' | sort -k1 > utilization.txt

# Combine both outputs
echo -e "APP\tCPU_REQUEST\tMEMORY_REQUEST\tCPU_LIMIT\tMEMORY_LIMIT\tCPU_UTILIZATION\tMEMORY_UTILIZATION"
join -1 1 -2 1 resources.txt utilization.txt | awk '{printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n", $1, $2, $3, $4, $5, $6, $7}'

