import logging
import subprocess
from kubernetes import client, config
import os
import json, requests

# Initialize Kubernetes API clients
config.load_kube_config()
class K8sAPI:
    def __init__(self):
        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()

k8s_api = K8sAPI()

SLACK_WEBHOOK_URL = 'webhook'

def send_slack_message(channel: str, text: str, is_channel_message: bool = False):
    """
    Send a Slack message via Incoming Webhook. 
    If is_channel_message, include channel override.
    """
    payload = {"text": text}
    if is_channel_message:
        payload["channel"] = channel
    response = requests.post(SLACK_WEBHOOK_URL, data=json.dumps(payload))
    response.raise_for_status()

from datetime import datetime

logger = logging.getLogger(__name__)

class ClusterAnalyzer:
    """
    Analyzes Kubernetes cluster nodes using kluster-capacity to identify drainable nodes
    and generates remediation steps.
    """
    def __init__(self):
        self.core_v1 = k8s_api.core_v1
        self.apps_v1 = k8s_api.apps_v1
        self.slack_channel = "channelid"

    def _filter_schedulable(self, nodes):
        """Remove nodes marked SchedulingDisabled"""
        schedulable = []
        for name in nodes:
            try:
                node = self.core_v1.read_node(name)
                if not node.spec.unschedulable:
                    schedulable.append(name)
            except client.exceptions.ApiException:
                logger.warning(f"Failed reading node {name}")
        return schedulable

    def get_raw_recommendations(self):
        """Run kluster-capacity cluster compression (cc) to get drainable node names"""
        try:
            res = subprocess.run(
                ["kluster-capacity", "cc"],
                capture_output=True, text=True, check=True
            )
            return [line.strip() for line in res.stdout.splitlines() if line.strip()]
        except subprocess.CalledProcessError as e:
            logger.error(f"kluster-capacity cc failed: {e.stderr}")
            return []

    def analyze_drainable(self):
        """
        Determine how many and which nodes can be drained, ignoring unschedulable ones.
        Returns:
            count: int
            nodes: list[str]
        """
        raw = self.get_raw_recommendations()
        candidates = self._filter_schedulable(raw)
        return len(candidates), candidates

    def _get_node_deployments(self, node):
        """List deployments backing pods on a node"""
        names = set()
        pods = self.core_v1.list_pod_for_all_namespaces(
            field_selector=f"spec.nodeName={node}"
        ).items
        for pod in pods:
            for ref in pod.metadata.owner_references or []:
                if ref.kind == "ReplicaSet":
                    rs = self.apps_v1.read_namespaced_replica_set(
                        ref.name, pod.metadata.namespace
                    )
                    for r2 in rs.metadata.owner_references or []:
                        if r2.kind == "Deployment":
                            names.add(r2.name)
        return list(names)

    def generate_report(self):
        """Create human-readable summary and kubectl steps"""
        count, nodes = self.analyze_drainable()
        ts = datetime.utcnow().isoformat() + "Z"
        lines = [f"*Cluster Optimization Report* (at {ts})\n"]
        if count:
            lines.append(f"{count} node(s) can be safely drained:")
            for n in nodes:
                lines.append(f"- {n}")
            lines.append("\nSteps for each node:")
            for n in nodes:
                deps = self._get_node_deployments(n)
                steps = [
                    f"kubectl describe node {n}",
                    f"kubectl cordon {n}"
                ]
                for d in deps:
                    steps.append(f"kubectl rollout restart deployment/{d}")
                steps.append(f"kubectl drain {n} --ignore-daemonsets --delete-emptydir-data")
                lines.append("```bash")
                lines.extend(steps)
                lines.append("```\n")
        else:
            lines.append("No drainable nodes detected.")
        return "\n".join(lines)

    def send_daily_report(self):
        try:
            text = self.generate_report()
            send_slack_message(channel=self.slack_channel, text=text, is_channel_message=True)
            logger.info("Daily cluster report sent.")
        except Exception as e:
            logger.error(f"Failed to send report: {e}")

if __name__ == '__main__':
    ca = ClusterAnalyzer()
    ca.send_daily_report()
    print(ca.generate_report())
