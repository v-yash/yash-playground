from typing import Optional
from kubernetes.client import ApiException, CoreV1Api
from kubernetes.client.api_client import ApiClient

class GetNodes:
    @staticmethod
    def get_nodes(logger: object, k8s_config: object) -> Optional[object]:
        """Get node information from Kubernetes API."""
        try:
            logger.info("Fetching node details...")
            api = CoreV1Api(ApiClient(k8s_config))
            return api.list_node(timeout_seconds=10)
        except ApiException as e:
            logger.error(f"Failed to get node list: {e}")
            return None