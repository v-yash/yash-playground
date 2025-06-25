from kubernetes import config, client
from typing import Optional

class KubeConfig:
    @staticmethod
    def load_kube_config(output: str, logger: Optional[object] = None) -> Optional[object]:
        """Load Kubernetes configuration from either kubeconfig or in-cluster."""
        try:
            try:
                if logger:
                    logger.info("Loading kubeconfig from environment...")
                config.load_kube_config()
                configuration = client.Configuration().get_default_copy()
                configuration.verify_ssl = False
                return configuration
            except config.ConfigException:
                if logger:
                    logger.info("Loading in-cluster configuration...")
                return config.load_incluster_config()
        except Exception as e:
            if logger:
                logger.error(f"Failed to load Kubernetes config: {e}")
            else:
                print(f"[ERROR] Failed to load Kubernetes config: {e}")
            return None