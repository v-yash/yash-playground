#!/usr/bin/env python3

"""
Kubernetes Cluster Resource Analyzer
A comprehensive tool for analyzing resource usage in Kubernetes clusters.
"""

import os
import sys
import time
import math
import argparse
import urllib3
from datetime import datetime
from typing import List, Dict, Tuple, Optional

from modules.logging import Logger
from modules.getopts import GetOpts
from modules.kube_config import KubeConfig
from modules.get_custom_object import K8sCustomObjects
from modules.get_nodes import GetNodes
from modules.output import Output
from modules.get_ns import K8sNameSpace

start_time = time.time()
urllib3.disable_warnings()

class K8sResourceAnalyzer:
    def __init__(self, k8s_config: object, logger: object, output: str):
        self.logger = logger  
        self.k8s_config = k8s_config
        self.output = output
        self.api_client = K8sCustomObjects(self.output, self.k8s_config, self.logger)

    def get_nodes(self, sort: str) -> None:
        """Collects and analyzes resource usage by node."""
        data = [] 
        total_cpu_used, total_mem_used, total_cpu_capacity, total_mem_capacity, node_count = 0, 0, 0, 0, 0
        
        self.logger.info("Collecting node metrics...")
        node_metrics = self.api_client.get_custom_object_nodes()
        node_object = GetNodes.get_nodes(self.logger, self.k8s_config)
        
        for stats in node_metrics['items']:
            node_name = stats['metadata']['name']
            node_cpu, node_mem = 0, 0
            
            for node in node_object.items:
                if node.metadata.name == node_name:
                    node_cpu = int(node.status.capacity['cpu'])
                    node_mem = math.ceil(int(node.status.capacity['memory'].strip('Ki'))) / 1000000
                    node_role = node.metadata.labels.get('node.kubernetes.io/role', 'worker')
            
            used_cpu = math.ceil(int(stats['usage']['cpu'].strip('n')) / 1000000)
            
            if 'Mi' in stats['usage']['memory']:
                used_memory = round(int(stats['usage']['memory'].strip('Mi')) / 1000, 1)
            else:
                used_memory = round(int(stats['usage']['memory'].strip('Ki')) / 1000000, 1)            
            
            total_cpu_used += used_cpu
            total_mem_used += used_memory
            total_cpu_capacity += node_cpu
            total_mem_capacity += node_mem
            node_count += 1
            
            data.append([
                f"{node_name} [{node_role}]",
                f"{used_cpu}m",
                str(node_cpu),
                f"{used_memory}",
                f"{node_mem}"
            ])

        data = self._format_node_data(data, node_count, total_cpu_used, 
                                    total_cpu_capacity, total_mem_used, 
                                    total_mem_capacity)
        
        headers = ["NODE_NAME", "CPU_USED/TOTAL", "%AGE_CPU_USAGE", 
                  "MEM_USED/TOTAL(GB)", "%AGE_MEM_USAGE"]
        Output.print(data, headers, self.output)

    def _format_node_data(self, data: List[List[str]], node_count: int,
                         total_cpu_used: float, total_cpu_capacity: float,
                         total_mem_used: float, total_mem_capacity: float) -> List[List[str]]:
        """Helper method to format node data for output."""
        data = Output.bar(data)
        
        for x in data:
            x[1] = f"{x[1]}{Output.GREEN}/{x[2]}{Output.RESET}"
            x[3] = f"{x[3]}{Output.CYAN}/{x[4]}{Output.RESET}"
            x.pop(2)
            x.pop(3)
        
        data.append([])
        data.append([
            f"{Output.TOTAL}{node_count}",
            f"{math.ceil(total_cpu_used)}m/{math.ceil(total_cpu_capacity)}",
            '',
            f"{round(total_mem_used, 2)}/{math.ceil(total_mem_capacity)} GB",
            ''
        ])
        return data

    def get_pods(self) -> Dict:
        """Retrieve pod metrics from the cluster."""
        return self.api_client.get_custom_object_pods()

    def get_resource_usage_by_pod(self, sort: str, filter_str: str) -> None:
        """Analyze resource usage by pod with optional filtering."""
        data, total_cpu, total_mem = [], 0, 0
        pod_details = self.get_pods()
        filter_list = filter_str.split(',') if ',' in filter_str else [filter_str]
        
        for stats in pod_details['items']:
            if not any(x in stats['metadata']['name'] for x in filter_list):
                continue
                
            cpu, mem = self._calculate_pod_resources(stats)
            total_cpu += cpu
            total_mem += mem                      
            data.append([
                stats['metadata']['name'],
                f"{math.ceil(cpu)}m",
                f"{round(mem, 2)}Mi",
                stats['metadata']['namespace']
            ])

        self._print_pod_data(data, sort, total_cpu, total_mem)

    def _calculate_pod_resources(self, pod_stats: Dict) -> Tuple[float, float]:
        """Calculate CPU and memory usage for a pod."""
        cpu, mem = 0, 0
        for container in pod_stats['containers']:
            if 'u' in container['usage']['cpu']:
                cpu += int(container['usage']['cpu'].strip('u')) / 1000000000
            else:
                cpu += int(container['usage']['cpu'].strip('n')) / 1000000
            
            if 'Mi' in container['usage']['memory']:
                mem += int(container['usage']['memory'].strip('Mi')) 
            else:
                mem += int(container['usage']['memory'].strip('Ki')) / 1000
        return cpu, mem

    def _print_pod_data(self, data: List[List[str]], sort: str, 
                       total_cpu: float, total_mem: float) -> None:
        """Format and print pod data."""
        headers = ["POD_NAME", "CPU_USED", "MEMORY_USED(MB)", "NAMESPACE"]
        data = Output.sort_data(data, sort)
        data.append([])
        data.append([
            f"{Output.TOTAL}{len(data)-1}",
            f"{math.ceil(total_cpu)}m",
            f"{round(total_mem / 1000, 2)} GB",
            ''
        ])
        Output.print(data, headers, self.output)

    def get_resource_usage_by_ns(self, sort: str) -> None:
        """Analyze resource usage aggregated by namespace."""
        data = []
        total_cpu, total_mem, ns_count = 0, 0, 0

        ns_details = K8sNameSpace.get_ns(self.logger, self.k8s_config)
        pod_details = self.get_pods()
        
        for namespace in ns_details.items:
            ns_cpu, ns_mem = self._calculate_namespace_resources(namespace.metadata.name, pod_details)
            total_cpu += ns_cpu
            total_mem += ns_mem
            ns_count += 1  
            data.append([
                namespace.metadata.name,
                f"{ns_cpu}m",
                f"{round(ns_mem / 1000, 2)}"
            ])

        self._print_namespace_data(data, sort, ns_count, total_cpu, total_mem)

    def _calculate_namespace_resources(self, namespace: str, pod_details: Dict) -> Tuple[int, float]:
        """Calculate resource usage for a namespace."""
        ns_cpu, ns_mem = 0, 0
        for stats in pod_details['items']:
            if stats['metadata']['namespace'] != namespace:
                continue
                
            pod_cpu, pod_mem = 0, 0
            for container in stats['containers']:
                if 'u' in container['usage']['cpu']:
                    pod_cpu += math.ceil(int(container['usage']['cpu'].strip('u')) / 1000000000)
                else:
                    pod_cpu += math.ceil(int(container['usage']['cpu'].strip('n'))) / 1000000
                
                if 'Mi' in container['usage']['memory']:
                    pod_mem += int(container['usage']['memory'].strip('Mi'))
                else:
                    pod_mem += round(int(container['usage']['memory'].strip('Ki')) / 1000, 2)
                
                ns_mem += pod_mem
                ns_cpu += pod_cpu
        return ns_cpu, ns_mem

    def _print_namespace_data(self, data: List[List[str]], sort: str,
                            ns_count: int, total_cpu: float, 
                            total_mem: float) -> None:
        """Format and print namespace data."""
        data = Output.sort_data(data, sort)
        
        for line in data:
            line.insert(2, f"{total_cpu}m")
            line.append(f"{round(total_mem / 1000, 2)}")
        
        data = Output.bar(data)
        
        for line in data:
            line.pop(2)
            line.pop(3)
        
        data.append([])        
        data.append([
            f"{Output.TOTAL}{ns_count}",
            f"{math.ceil(total_cpu)}m",
            '',
            f"{round(total_mem / 1000, 2)} GB"
        ])
        
        headers = ["NAMESPACE", "CPU_USED", "%AGE_NS_TOTAL_CPU", 
                  "MEMORY_USED(GB)", "%AGE_NS_TOTAL_MEM"]
        Output.print(data, headers, self.output)

    def get_namespaced_resource_usage(self, namespace: str, sort: str) -> None:
        """Analyze resource usage within specific namespace(s)."""
        ns_list = namespace.split(',') if ',' in namespace else [namespace]
        
        for ns in ns_list:
            data, total_cpu, total_mem, total_pods = [], 0, 0, 0
            pod_details = self.api_client.get_custom_object_namespaced_pods(self.output, ns)
            
            for stats in pod_details['items']:
                cpu, mem = self._calculate_pod_resources(stats)
                total_cpu += cpu
                total_mem += mem
                total_pods += 1                 
                data.append([
                    stats['metadata']['name'],
                    f"{math.ceil(cpu)}m",
                    round(mem, 2),
                    ns
                ])
            
            self._print_pod_data(data, sort, total_cpu, total_mem)

def main():
    try:
        options = GetOpts.get_opts()
        logger = Logger.get_logger(options[3])
        k8s_config = KubeConfig.load_kube_config(options[3], logger)
        analyzer = K8sResourceAnalyzer(k8s_config, logger, options[3])
        
        if options[0]:  # Help option
            _display_help()
            return
        
        # options = [help, pods, ns, output, sort, filter]
        if 'namespace' in options[5] and not options[2]:
            analyzer.get_resource_usage_by_ns(options[4])
        elif options[5] or options[1]:
            pods = options[5] or options[1]
            analyzer.get_resource_usage_by_pod(options[4], pods)
        elif options[2]:
            analyzer.get_namespaced_resource_usage(options[2], options[4])
        else:  
            analyzer.get_nodes(options[4])
            analyzer.get_resource_usage_by_ns(options[4])
            
        Output.time_taken(start_time)
        
    except KeyboardInterrupt:
        print("\n[INFO] Analysis interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        sys.exit(1)

def _display_help():
    """Display help information for the script."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""Kubernetes Cluster Resource Analyzer
A comprehensive tool for analyzing resource usage in Kubernetes clusters.

Before running script export KUBECONFIG file as env:
    export KUBECONFIG=<kubeconfig file location>
    
Example:
    export KUBECONFIG=/path/to/kubeconfig""",
        epilog="To get more options, please raise it in issues section of the repository.")
    
    parser.add_argument('-s', '--sort', choices=['cpu', 'mem'], 
                      help="Sort by cpu or memory. Default is by name.")
    parser.add_argument('-n', '--namespace', 
                      help="Analyze specific namespace(s). Comma-separated list supported.")
    parser.add_argument('-f', '--filter', 
                      help="Filter resource usage by pod name(s). Comma-separated list supported.")
    parser.add_argument('-o', '--output', choices=['text', 'csv', 'json', 'tree'], default='text',
                      help="Output format. Default is text.")
    parser.add_argument('-p', '--pods', 
                      help="Filter by pod name(s). Comma-separated list supported.")        
    parser.parse_args()

if __name__ == "__main__":
    main()