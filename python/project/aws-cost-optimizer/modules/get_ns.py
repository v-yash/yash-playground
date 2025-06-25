from typing import Optional
from kubernetes.client import ApiException, CoreV1Api
from kubernetes.client.api_client import ApiClient

class K8sNameSpace:
    @staticmethod
    def get_ns(logger: object, k8s_config: object) -> Optional[object]:
        """Get namespace information from Kubernetes API."""
        try:
            logger.info("Fetching namespace details...")
            api = CoreV1Api(ApiClient(k8s_config))
            return api.list_namespace(timeout_seconds=10)
        except ApiException as e:
            logger.error(f"Failed to get namespace list: {e}")
            return None