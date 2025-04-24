from kubernetes.client import CoreV1Api, AppsV1Api
from kubernetes.config import load_incluster_config
import logging
import re
import datetime

logger = logging.getLogger(__name__)

class KubernetesAPI:
    def __init__(self):
        try:
            load_incluster_config()
            self.core_v1 = CoreV1Api()
            self.apps_v1 = AppsV1Api()
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {str(e)}")
            raise

    def execute_command(self, command_parts):
        """Execute kubectl command safely using Kubernetes API"""
        try:
            # Remove kubectl prefix if present
            if command_parts and command_parts[0] == "kubectl":
                command_parts = command_parts[1:]

            # Handle rollout restart first
            if len(command_parts) >= 2 and command_parts[0] == "rollout" and command_parts[1] == "restart":
                return self._handle_restart(command_parts[2:])
            
            # Validate command structure
            if len(command_parts) < 2:
                raise ValueError("Invalid command format")
                
            cmd_type = command_parts[0]
            full_resource = command_parts[1]
            
            # Split resource type/name with validation
            if "/" in full_resource:
                resource_type, resource_name = full_resource.split("/", 1)
                if not resource_name:
                    raise ValueError("Missing resource name after '/'")
            else:
                resource_type = full_resource
                resource_name = None

            # Supported commands and resources
            allowed_commands = {
                "get": ["pods", "deployments", "namespaces"],
                "describe": ["pod", "deployment"],
                "rollout": ["restart"]
            }

            ALLOWED_EXEC_COMMANDS = ["ls", "df", "date"]

            # Validate command type
            if cmd_type not in allowed_commands:
                raise ValueError(f"Unsupported command type: {cmd_type}")
                
            # Validate resource type
            if resource_type not in allowed_commands[cmd_type]:
                raise ValueError(f"Unsupported resource type for {cmd_type}: {resource_type}. Allowed: {allowed_commands[cmd_type]}")

            # Validate resource name format
            if resource_name and not re.match(r'^[a-zA-Z0-9-]+$', resource_name):
                raise ValueError(f"Invalid resource name: {resource_name}")
                
            # Execute command
            if cmd_type == "get":
                return self._handle_get(full_resource, command_parts[2:])
            elif cmd_type == "describe":
                return self._handle_describe(full_resource, command_parts[2:])
            elif cmd_type == "logs":
                return self._handle_logs(full_resource, command_parts[2:])
                
        except Exception as e:
            logger.error(f"Command failed: {str(e)}")
            return f"Error: {str(e)}"

    def _handle_restart(self, args):
        """Handle rollout restart deployment command"""
        if not args or not args[0].startswith("deployment/"):
            raise ValueError("Restart command requires deployment name")
            
        deploy_name = args[0].split("/")[1]
        namespace = self._extract_namespace(args[1:])
        
        try:
            self.apps_v1.patch_namespaced_deployment(
                name=deploy_name,
                namespace=namespace,
                body={"spec": {"template": {"metadata": {"annotations": {
                    "kubectl.kubernetes.io/restartedAt": datetime.datetime.now().isoformat()
                }}}}}
            )
            return f"Successfully restarted deployment/{deploy_name} in {namespace}"
        except Exception as e:
            raise ValueError(f"Failed to restart deployment: {str(e)}")

    # def _handle_exec(pod_name, command):
    #     if command not in ALLOWED_EXEC_COMMANDS:
    #         raise ValueError("Command not permitted")
        
    #     return self.core_v1.connect_get_namespaced_pod_exec(
    #         pod_name, 
    #         namespace=namespace,
    #         command=["/bin/sh", "-c", command],
    #         stderr=True, 
    #         stdin=False, 
    #         stdout=True, 
    #         tty=False
    #     )

    def _handle_get(self, resource, args):
        namespace = self._extract_namespace(args)
        field_selector = None
        # Parse field selector from args
        for i in range(len(args)):
            if args[i] == '--field-selector' and i + 1 < len(args):
                field_selector = args[i + 1]
                break

        if "/" in resource:
            raise ValueError("Use 'describe' command for detailed resource information")
        else:
            if resource == "pods":
                pods = self.core_v1.list_namespaced_pod(
                    namespace=namespace,
                    field_selector=field_selector if field_selector else "status.phase=Running"
                )
                return "\n".join(pod.metadata.name for pod in pods.items)
            elif resource == "deployments":
                deployments = self.apps_v1.list_namespaced_deployment(
                    namespace=namespace,
                    field_selector=field_selector
                )
                return "\n".join(deploy.metadata.name for deploy in deployments.items)
            elif resource == "namespaces":
                namespaces = self.core_v1.list_namespace(field_selector=field_selector)
                return "\n".join(ns.metadata.name for ns in namespaces.items)
            else:
                raise ValueError(f"Unsupported resource: {resource}")

    def _handle_describe(self, resource, args):
        namespace = self._extract_namespace(args)
        if "/" not in resource:
            raise ValueError("Invalid resource format. Use: describe pod/<name> or describe deployment/<name>")

        resource_type, resource_name = resource.split("/", 1)
        if resource_type == "pod":
            pod = self.core_v1.read_namespaced_pod(resource_name, namespace)
            # Extract key details
            details = f"""
                Name: {pod.metadata.name}
                Status: {pod.status.phase}
                IP: {pod.status.pod_ip}
                Node: {pod.spec.node_name}
                Containers: {[c.name for c in pod.spec.containers]}
                Creation Time: {pod.metadata.creation_timestamp}
            """
            return details
        elif resource_type == "deployment":
            deployment = self.apps_v1.read_namespaced_deployment(resource_name, namespace)
            return f"📋 *Deployment Details*: `{resource_name}`\n```\n{deployment}\n```"
        else:
            raise ValueError(f"Unsupported resource type for describe: {resource_type}")

    def _extract_namespace(self, args):
        """Extract namespace from args if present"""
        if "-n" in args:
            idx = args.index("-n")
            if idx + 1 < len(args):
                return args[idx + 1]
        return "default"

# Initialize singleton instance
k8s_api = KubernetesAPI()

def get_pods(namespace="default", limit=50):
    """Get pods with limit and field selector"""
    try:
        pods = k8s_api.core_v1.list_namespaced_pod(
            namespace=namespace,
            limit=limit,
            field_selector="status.phase=Running"  # Only show running pods
        )
        return [pod.metadata.name for pod in pods.items][:limit]
    except Exception as e:
        logger.error(f"Failed to get pods: {str(e)}")
        return ["Error fetching pods"]

def get_deployments(namespace="default", limit=50):
    """Get deployments with limit"""
    try:
        deployments = k8s_api.apps_v1.list_namespaced_deployment(
            namespace=namespace,
            limit=limit
        )
        return [deploy.metadata.name for deploy in deployments.items][:limit]
    except Exception as e:
        logger.error(f"Failed to get deployments: {str(e)}")
        return ["Error fetching deployments"]

def execute_safe_kubectl(command):
    """Execute command with proper error handling"""
    try:
        if not isinstance(command, str):
            raise ValueError("Command must be a string")
            
        # Split command into parts and validate
        parts = command.split()
        if not parts:
            raise ValueError("Empty command")
            
        return k8s_api.execute_command(parts)
    except Exception as e:
        logger.error(f"Command validation failed: {str(e)}")
        return f"Error: {str(e)}"
    
def search_pods(name_pattern, namespace="default"):
    """Search for pods using partial match"""
    try:
        all_pods = k8s_api.core_v1.list_namespaced_pod(namespace)
        return [p.metadata.name for p in all_pods.items
                if name_pattern.lower() in p.metadata.name.lower()][:20]
    except Exception as e:
        logger.error(f"Pod search failed: {str(e)}")
        return []

def search_deployments(name_pattern, namespace="default"):
    """Search for deployments using partial match"""
    try:
        all_deployments = k8s_api.apps_v1.list_namespaced_deployment(namespace)
        return [d.metadata.name for d in all_deployments.items
                if name_pattern.lower() in d.metadata.name.lower()][:20]
    except Exception as e:
        logger.error(f"Deployment search failed: {str(e)}")
        return []