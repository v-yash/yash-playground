from typing import Dict, Optional
from kubernetes.client import ApiException, CustomObjectsApi
from kubernetes.client.api_client import ApiClient

class K8sCustomObjects:
    def __init__(self, output: str, k8s_config: object, logger: object):
        self.output = output
        self.logger = logger
        self.k8s_config = k8s_config
        self.api = CustomObjectsApi(ApiClient(self.k8s_config))

    def get_custom_object_nodes(self) -> Dict:
        """Get node metrics from metrics-server."""
        try:
            self.logger.info("Fetching node metrics...")
            return self.api.list_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="nodes"
            )
        except ApiException as e:
            self.logger.error(f"Failed to get node metrics: {e}")
            raise

    def get_custom_object_pods(self) -> Dict:
        """Get pod metrics from metrics-server."""
        try:
            self.logger.info("Fetching pod metrics...")
            return self.api.list_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="pods"
            )
        except ApiException as e:
            self.logger.error(f"Failed to get pod metrics: {e}")
            raise

    def get_custom_object_namespaced_pods(self, namespace: str) -> Dict:
        """Get pod metrics for specific namespace."""
        try:
            self.logger.info(f"Fetching pod metrics for namespace {namespace}...")
            return self.api.list_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                namespace=namespace,
                plural="pods"
            )
        except ApiException as e:
            self.logger.error(f"Failed to get pod metrics for {namespace}: {e}")
            raise