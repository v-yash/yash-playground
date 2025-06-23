from kubernetes.client import CoreV1Api, AppsV1Api, AutoscalingV1Api, CustomObjectsApi
from kubernetes.config import load_incluster_config
import logging
import re
import datetime
from datetime import timezone
import threading
import time
from functools import lru_cache
import subprocess
from kubernetes.stream import stream

logger = logging.getLogger(__name__)

pod_search_cache = {"names": [], "lower": []}
deployment_search_cache = {"names": [], "lower": []}
cache_lock = threading.Lock()
CACHE_REFRESH_INTERVAL = 15

class KubernetesAPI:
    def __init__(self):
        try:
            print("Initializing Kubernetes API client...")
            load_incluster_config()
            self.core_v1 = CoreV1Api()
            self.apps_v1 = AppsV1Api()
            self.autoscaling_v1 = AutoscalingV1Api()
            self.custom_metrics = CustomObjectsApi()
            print("Kubernetes API client initialized successfully")
        except Exception as e:
            print(f"ERROR: Failed to initialize Kubernetes client: {str(e)}")
            logger.error(f"Failed to initialize Kubernetes client: {str(e)}")
            raise

    def execute_command(self, command_parts):
        """Execute kubectl command safely using Kubernetes API"""
        print(f"Executing command: {' '.join(command_parts)}")
        logger.info(f"Executing command: {' '.join(command_parts)}")
        try:
            # Remove kubectl prefix if present
            if command_parts and command_parts[0] == "kubectl":
                command_parts = command_parts[1:]

            # Handle rollout restart first
            if len(command_parts) >= 2 and command_parts[0] == "rollout" and command_parts[1] == "restart":
                print("Handling rollout restart command")
                return self._handle_restart(command_parts[2:])
            
            # Validate command structure
            if len(command_parts) < 2:
                error_msg = "Invalid command format"
                print(f"ERROR: {error_msg}")
                raise ValueError(error_msg)
                
            cmd_type = command_parts[0]
            full_resource = command_parts[1]
            
            # Split resource type/name with validation
            if "/" in full_resource:
                resource_type, resource_name = full_resource.split("/", 1)
                if not resource_name:
                    error_msg = "Missing resource name after '/'"
                    print(f"ERROR: {error_msg}")
                    raise ValueError(error_msg)
            else:
                resource_type = full_resource
                resource_name = None

            # Supported commands and resources
            allowed_commands = {
                "get": ["pods", "deployments", "namespaces"],
                "describe": ["pod", "deployment"],
                "rollout": ["restart"],
                "scale": ["deployment"],
                "exec": ["pod"]
            }

            # Validate command type
            if cmd_type not in allowed_commands:
                error_msg = f"Unsupported command type: {cmd_type}"
                print(f"ERROR: {error_msg}")
                raise ValueError(error_msg)
                
            # Validate resource type
            if resource_type not in allowed_commands[cmd_type]:
                error_msg = f"Unsupported resource type for {cmd_type}: {resource_type}. Allowed: {allowed_commands[cmd_type]}"
                print(f"ERROR: {error_msg}")
                raise ValueError(error_msg)

            # Validate resource name format
            if resource_name and not re.match(r'^[a-zA-Z0-9-]+$', resource_name):
                error_msg = f"Invalid resource name: {resource_name}"
                print(f"ERROR: {error_msg}")
                raise ValueError(error_msg)
                
            # Execute command
            print(f"Executing {cmd_type} command for {resource_type}/{resource_name if resource_name else ''}")
            if cmd_type == "get":
                return self._handle_get(full_resource, command_parts[2:])
            elif cmd_type == "scale":
                return self._handle_scale(resource_type, resource_name, command_parts[2:])
            elif cmd_type == "describe":
                return self._handle_describe(full_resource, command_parts[2:])
            elif cmd_type == "exec":
                try:
                    dash_index = command_parts.index('--')
                    exec_args = command_parts[dash_index+1:]
                except ValueError:
                    exec_args = command_parts[2:]
                return self._handle_exec(resource_type, resource_name, exec_args)
                
        except Exception as e:
            print(f"ERROR in execute_command: {str(e)}")
            logger.error(f"Command failed: {str(e)}")
            return f"Error: {str(e)}"

    def _handle_restart(self, args):
        """Handle rollout restart deployment command"""
        print("Handling rollout restart command")
        logger.info("Handling rollout restart command")
        if not args or not args[0].startswith("deployment/"):
            error_msg = "Restart command requires deployment name"
            print(f"ERROR: {error_msg}")
            raise ValueError(error_msg)
            
        deploy_name = args[0].split("/")[1]
        namespace = "default"
        print(f"Restarting deployment: {deploy_name} in namespace: {namespace}")
        
        try:
            self.apps_v1.patch_namespaced_deployment(
                name=deploy_name,
                namespace=namespace,
                body={"spec": {"template": {"metadata": {"annotations": {
                    "kubectl.kubernetes.io/restartedAt": datetime.datetime.now().isoformat()
                }}}}}
            )
            print(f"Successfully restarted deployment/{deploy_name}")
            return f"Successfully restarted deployment/{deploy_name} in {namespace}"
        except Exception as e:
            error_msg = f"Failed to restart deployment: {str(e)}"
            print(f"ERROR: {error_msg}")
            raise ValueError(error_msg)

    def _handle_get(self, resource, args):
        print(f"Handling get command for resource: {resource}")
        logger.info("Handling get command")
        namespace = "default"
        field_selector = None
        # Parse field selector from args
        for i in range(len(args)):
            if args[i] == '--field-selector' and i + 1 < len(args):
                field_selector = args[i + 1]
                break

        if "/" in resource:
            error_msg = "Use 'describe' command for detailed resource information"
            print(f"ERROR: {error_msg}")
            raise ValueError(error_msg)
        else:
            if resource == "pods":
                print(f"Fetching pods in namespace: {namespace}")
                pods = self.core_v1.list_namespaced_pod(
                    namespace=namespace,
                    field_selector=field_selector if field_selector else "status.phase=Running"
                )
                print(f"Found {len(pods.items)} pods")
                pod_list = []
                for pod in pods.items:
                    name = pod.metadata.name
                    status = pod.status.phase
                    restart_count = sum(
                        (cs.restart_count for cs in (pod.status.container_statuses or []))
                    )
                    creation_time = pod.metadata.creation_timestamp
                    age_seconds = (datetime.datetime.now(timezone.utc) - creation_time).total_seconds()
                    age_minutes = int(age_seconds // 60)

                    pod_info = f"{name} | {status} | Restarts: {restart_count} | Age: {age_minutes} min"
                    pod_list.append(pod_info)

                return "\n".join(pod_list)

            elif resource == "deployments":
                print(f"Fetching deployments in namespace: {namespace}")
                deployments = self.apps_v1.list_namespaced_deployment(
                    namespace=namespace,
                    field_selector=field_selector
                )
                print(f"Found {len(deployments.items)} deployments")
                return "\n".join(deploy.metadata.name for deploy in deployments.items)

            elif resource == "namespaces":
                print("Fetching namespaces")
                namespaces = self.core_v1.list_namespace(field_selector=field_selector)
                print(f"Found {len(namespaces.items)} namespaces")
                return "\n".join(ns.metadata.name for ns in namespaces.items)

            else:
                error_msg = f"Unsupported resource: {resource}"
                print(f"ERROR: {error_msg}")
                raise ValueError(error_msg)

    def _handle_scale(self, resource_type, resource_name, args):
        print(f"Handling scale command for {resource_type}/{resource_name}")
        logger.info("Handling scale command")
        namespace = "default"

        if "/" in resource_name:
            resource_type, resource_name = resource_name.split("/", 1)
        
        if resource_type != "deployment":
            error_msg = "Scale is only supported for deployments."
            print(f"ERROR: {error_msg}")
            raise ValueError(error_msg)
        if not resource_name:
            error_msg = "Deployment name required for scaling."
            print(f"ERROR: {error_msg}")
            raise ValueError(error_msg)

        # Get replica count
        replica_count = None
        for arg in args:
            if arg.startswith("--replicas="):
                replica_count = int(arg.split("=")[1])
            elif arg.isdigit():
                replica_count = int(arg)

        if replica_count is None:
            error_msg = "Replica count not specified or invalid."
            print(f"ERROR: {error_msg}")
            raise ValueError(error_msg)

        print(f"Attempting to scale {resource_name} to {replica_count} replicas")

        # Check HPA constraints if exists
        try:
            print(f"Checking HPA constraints for {resource_name}")
            hpa = self.autoscaling_v1.read_namespaced_horizontal_pod_autoscaler(
                name=resource_name,
                namespace=namespace
            )
            if replica_count > hpa.spec.max_replicas:
                error_msg = f"Cannot exceed HPA max replicas ({hpa.spec.max_replicas})"
                print(f"ERROR: {error_msg}")
                raise ValueError(error_msg)
            if replica_count < hpa.spec.min_replicas:
                error_msg = f"Cannot go below HPA min replicas ({hpa.spec.min_replicas})"
                print(f"ERROR: {error_msg}")
                raise ValueError(error_msg)
        except Exception as e:
            if "Not Found" not in str(e):
                error_msg = f"HPA verification failed: {str(e)}"
                print(f"ERROR: {error_msg}")
                raise ValueError(error_msg)

        # Execute scaling
        try:
            print(f"Executing scale operation for {resource_name} to {replica_count} replicas")
            self.apps_v1.patch_namespaced_deployment_scale(
                name=resource_name,
                namespace=namespace,
                body={"spec": {"replicas": replica_count}}
            )
            print(f"Successfully scaled {resource_name} to {replica_count} replicas")
            return f"✅ Scaled deployment `{resource_name}` to {replica_count} replicas in `{namespace}`"
        except Exception as e:
            error_msg = f"Failed to scale deployment: {str(e)}"
            print(f"ERROR: {error_msg}")
            raise ValueError(error_msg)

    def _handle_exec(self, resource_type, resource_name, args):
        """Handle exec command in a pod using Kubernetes Python client"""
        print(f"Handling exec command for {resource_type}/{resource_name}")
        logger.info(f"Handling exec command for {resource_name} with args: {args}")
        
        # Constants for output management
        MAX_OUTPUT_LENGTH = 2000  # Keep under Slack's 4000 character limit
        MAX_LINES = 100           # Maximum lines to return
        TRUNCATE_MSG = "\n...[output truncated - showing last {} lines]...\n"
        SHELL_OPERATORS = {'|', '&', '>', '<', ';', '&&', '||', '`', '$'}

        # Blocked command patterns
        BLOCKED_COMMANDS = {
            'psql': "Database access via psql is not permitted",
            'mysql': "Database access via mysql is not permitted",
            'mongo': "Database access via mongo is not permitted",
            'redis-cli': "Database access via redis-cli is not permitted",
            'nc ': "Netcat commands are not permitted",
            'curl': "Direct curl commands are not permitted",
            'wget': "Direct wget commands are not permitted",
            'ssh ': "SSH commands are not permitted",
        }
        
        # Blocked sensitive patterns (case insensitive)
        BLOCKED_PATTERNS = [
            r'password\s*=\s*',
            r'pwd\s*=\s*',
            r'secret\s*=\s*',
            r'passwd\s*',
            r'export\s+\w*password\w*',
        ]
        
        # Validation
        if resource_type != "pod":
            error_msg = "Exec is only supported for pods."
            logger.error(error_msg)
            raise ValueError(error_msg)
        if not resource_name:
            error_msg = "Pod name required for exec."
            logger.error(error_msg)
            raise ValueError(error_msg)
        if not args:
            error_msg = "No command provided to execute in the pod."
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Prepare the command strings
        original_command_str = ' '.join(args)
        check_command_str = original_command_str.lower()

        # Security validation
        # 1. Check blocked commands
        for cmd, msg in BLOCKED_COMMANDS.items():
            if check_command_str.startswith(cmd.lower()):
                logger.error(f"Blocked command attempt: {original_command_str}")
                raise ValueError(f"Security violation: {msg}")
        
        # 2. Check blocked patterns
        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, check_command_str, re.IGNORECASE):
                logger.error(f"Blocked sensitive pattern in: {original_command_str}")
                raise ValueError("Security violation: Sensitive pattern detected")

        # Determine if shell execution is needed
        needs_shell = any(op in original_command_str for op in SHELL_OPERATORS)
        
        if needs_shell:
            command_to_exec = ["sh", "-c", original_command_str]
            logger.info(f"Executing as shell command: {original_command_str}")
        else:
            command_to_exec = args
            logger.info(f"Executing direct command: {original_command_str}")

        try:
            # Execute command in pod
            resp = stream(
                self.core_v1.connect_get_namespaced_pod_exec,
                name=resource_name,
                namespace="default",
                command=command_to_exec,
                stderr=True,
                stdin=False,
                stdout=True,
                tty=False,
                _preload_content=False
            )

            # Process output
            output_buffer = []
            line_count = 0
            
            while resp.is_open():
                resp.update(timeout=1)
                
                # Capture stdout
                if resp.peek_stdout():
                    line = resp.read_stdout()
                    output_buffer.append(line)
                    line_count += 1
                    
                # Capture stderr
                if resp.peek_stderr():
                    err_line = resp.read_stderr()
                    output_buffer.append(f"Error: {err_line}")
                    line_count += 1
                
                # Manage buffer size
                if line_count > MAX_LINES * 1.5:  # 1.5x buffer before trimming
                    keep_lines = MAX_LINES // 2
                    output_buffer = output_buffer[-keep_lines:]
                    line_count = keep_lines

            resp.close()

            # Prepare final output
            full_output = ''.join(output_buffer).strip()
            
            # Truncate if needed (keeping the end which is usually most relevant)
            if len(full_output) > MAX_OUTPUT_LENGTH:
                logger.info(f"Truncating long output ({len(full_output)} chars)")
                keep_chars = MAX_OUTPUT_LENGTH - len(TRUNCATE_MSG)
                full_output = TRUNCATE_MSG.format(MAX_LINES//2) + full_output[-keep_chars:]
            
            logger.info(f"Command execution completed successfully")
            return full_output or "Command executed successfully (no output)"

        except Exception as e:
            error_msg = f"Exec command failed: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _handle_describe(self, resource, args):
        print(f"Handling describe command for resource: {resource}")
        logger.info("Describe resource:", resource)
        namespace = "default"
        
        if "/" not in resource:
            error_msg = "Invalid resource format. Use: describe pod/<name> or describe deployment/<name>"
            print(f"ERROR: {error_msg}")
            raise ValueError(error_msg)

        resource_type, resource_name = resource.split("/", 1)
        print(f"Describing {resource_type}: {resource_name}")
        
        if resource_type == "pod":
            try:
                print(f"Fetching pod details for {resource_name}")
                pod = self.core_v1.read_namespaced_pod(resource_name, namespace)
                pod_labels = pod.metadata.labels or {}

                # Extract deployment name via ownerReference (ReplicaSet → Deployment)
                deployment_name = None
                try:
                    owners = pod.metadata.owner_references or []
                    for owner in owners:
                        if owner.kind == "ReplicaSet":
                            print(f"Found owner ReplicaSet: {owner.name}")
                            rs = self.apps_v1.read_namespaced_replica_set(owner.name, namespace)
                            rs_owners = rs.metadata.owner_references or []
                            for rs_owner in rs_owners:
                                if rs_owner.kind == "Deployment":
                                    deployment_name = rs_owner.name
                                    print(f"Found owner Deployment: {deployment_name}")
                                    break
                except Exception as e:
                    print(f"WARNING: Could not determine deployment for pod {resource_name}: {str(e)}")
                    logger.warning(f"Could not determine deployment for pod {resource_name}: {str(e)}")

                # Get pod metrics if metrics server is available
                metrics_info = "\nMetrics: Not available"        
                try:
                    pod_metrics = self.custom_metrics.get_namespaced_pod_metrics(resource_name, namespace, _request_timeout=3)
                    if pod_metrics.containers:
                        metrics_info = "\nMetrics:"
                        for container in pod_metrics.containers:
                            cpu = container.usage.get("cpu", "N/A")
                            memory = container.usage.get("memory", "N/A")
                            metrics_info += f"\n  {container.name}: CPU={cpu}, Memory={memory}"
                except Exception as e:
                    metrics_info = "\nMetrics: Error fetching - ensure metrics-server is installed"
                    print(f"Metrics error: {str(e)}")

                # HPA details if deployment found
                hpa_info = "Not Available"
                hpa_metrics = ""
                replicas_info = ""
                if deployment_name:
                    try:
                        print(f"Fetching HPA details for deployment {deployment_name}")
                        try:
                            hpas = self.autoscaling_v1.list_namespaced_horizontal_pod_autoscaler(namespace)
                            for hpa in hpas.items:
                                if hpa.spec.scale_target_ref.name == deployment_name:
                                    # Get current metrics if available
                                    current_metrics = []
                                    if hpa.status.current_cpu_utilization_percentage:
                                        current_metrics.append(f"CPU: {hpa.status.current_cpu_utilization_percentage}%")
                                    if hasattr(hpa.status, 'current_memory_utilization_percentage') and hpa.status.current_memory_utilization_percentage:
                                        current_metrics.append(f"Memory: {hpa.status.current_memory_utilization_percentage}%")
                                    
                                    hpa_info = (
                                        f"Target: {hpa.spec.target_cpu_utilization_percentage}%\n"
                                        f"Min Pods: {hpa.spec.min_replicas}, Max Pods: {hpa.spec.max_replicas}\n"
                                        f"Current Replicas: {hpa.status.current_replicas}"
                                    )
                                    
                                    if current_metrics:
                                        hpa_metrics = f"\nCurrent Utilization: {', '.join(current_metrics)}"
                                    
                                    print(f"Found HPA for deployment: {hpa_info}")
                                    break
                        except Exception as e:
                            print(f"WARNING: HPA access failed: {str(e)}")
                            logger.error(f"HPA access failed: {str(e)}")
                            hpa_info = "HPA details unavailable (missing permissions)"

                        print(f"Fetching deployment details for {deployment_name}")
                        deployment = self.apps_v1.read_namespaced_deployment(deployment_name, namespace)
                        replicas_info = (
                            f"\nDeployment: {deployment_name}\n"
                            f"Available Replicas: {deployment.status.available_replicas}\n"
                            f"Desired Replicas: {deployment.spec.replicas}"
                        )
                    except Exception as e:
                        print(f"WARNING: Failed to fetch HPA/deployment for {deployment_name}: {str(e)}")
                        logger.warning(f"Failed to fetch HPA/deployment for {deployment_name}: {str(e)}")

                # Get pod events
                events_info = "\nEvents: None"
                try:
                    events = self.core_v1.list_namespaced_event(
                        namespace,
                        field_selector=f"involvedObject.name={resource_name},involvedObject.kind=Pod"
                    )
                    if events.items:
                        events_info = "\nRecent Events:"
                        for event in sorted(events.items, key=lambda x: x.last_timestamp)[-3:]:
                            events_info += f"\n  {event.last_timestamp}: [{event.type}] {event.message}"
                    else:
                        events_info = "\nEvents: No recent events found"
                except Exception as e:
                    print(f"WARNING: Could not fetch pod events: {str(e)}")

                # Final pod details
                details = f"""```
Name: {pod.metadata.name}
Status: {pod.status.phase}
IP: {pod.status.pod_ip}
Node: {pod.spec.node_name}

-- Configuration --
Size: {pod_labels.get('podSize')}
Size_Type: {pod_labels.get('resourceAllocationStrategy')}
Containers: {[c.name for c in pod.spec.containers]}
Image: {[c.image for c in pod.spec.containers]}
Creation Time: {pod.metadata.creation_timestamp}

-- Deployment --
{replicas_info}

-- Autoscaling --
HPA: {hpa_info}{hpa_metrics}

-- Metrics --
{metrics_info}

-- Activity --
{events_info}
```"""
                print("Successfully generated pod description")
                return details
            
            except Exception as e:
                error_msg = f"Failed to describe pod: {str(e)}"
                print(f"ERROR: {error_msg}")
                raise ValueError(error_msg)
        
        else:
            error_msg = f"Unsupported resource type for describe: {resource_type}"
            print(f"ERROR: {error_msg}")
            raise ValueError(error_msg)

# Initialize singleton instance
print("Initializing Kubernetes API instance...")
k8s_api = KubernetesAPI()
print("Kubernetes API instance ready")

def get_pods(namespace="default", limit=50):
    """Get pods with limit and field selector"""
    print(f"Getting pods in namespace: {namespace} with limit: {limit}")
    try:
        pods = k8s_api.core_v1.list_namespaced_pod(
            namespace=namespace,
            limit=limit,
            field_selector="status.phase=Running"  # Only show running pods
        )
        print(f"Successfully fetched {len(pods.items)} pods")
        return [pod.metadata.name for pod in pods.items][:limit]
    except Exception as e:
        print(f"ERROR: Failed to get pods: {str(e)}")
        logger.error(f"Failed to get pods: {str(e)}")
        return ["Error fetching pods"]

def get_deployments(namespace="default", limit=50):
    """Get deployments with limit"""
    print(f"Getting deployments in namespace: {namespace} with limit: {limit}")
    try:
        deployments = k8s_api.apps_v1.list_namespaced_deployment(
            namespace=namespace,
            limit=limit
        )
        print(f"Successfully fetched {len(deployments.items)} deployments")
        return [deploy.metadata.name for deploy in deployments.items][:limit]
    except Exception as e:
        print(f"ERROR: Failed to get deployments: {str(e)}")
        logger.error(f"Failed to get deployments: {str(e)}")
        return ["Error fetching deployments"]

def execute_safe_kubectl(command):
    print(f"Executing kubectl command: {command}")
    logger.info(f"Executing kubectl command: {command}")
    try:
        if not isinstance(command, str):
            error_msg = "Command must be a string"
            print(f"ERROR: {error_msg}")
            raise ValueError(error_msg)
             
        parts = command.split()
        if not parts:
            error_msg = "Empty command"
            print(f"ERROR: {error_msg}")
            raise ValueError(error_msg)
 
        result = k8s_api.execute_command(parts)
        print(f"Command executed successfully. Result: {result[:200]}...")  # Truncate long output
        return result
    except Exception as e:
        print(f"ERROR: Failed to execute kubectl command: {str(e)}")
        logger.error(f"Failed to execute kubectl command: {str(e)}")
        raise
    
def start_cache_updater():
    """Background thread to refresh search data"""
    print("Starting cache updater thread")
    def updater():
        while True:
            try:
                print("Running cache refresh...")
                refresh_pod_cache()
                refresh_deployment_cache()
                print("Cache refresh completed")
            except Exception as e:
                print(f"ERROR in cache updater: {str(e)}")
                logger.error(f"Cache update failed: {str(e)}")
            time.sleep(CACHE_REFRESH_INTERVAL)

    thread = threading.Thread(target=updater, daemon=True)
    thread.start()
    print("Cache updater thread started")

def refresh_pod_cache():
    """Refresh pod cache with efficient query"""
    try:
        print("Refreshing pod cache...")
        pods = k8s_api.core_v1.list_namespaced_pod(
            namespace="default",
            field_selector="status.phase=Running",
            timeout_seconds=5
        ).items
        names = [p.metadata.name for p in pods]
        with cache_lock:
            pod_search_cache["names"] = names
            pod_search_cache["lower"] = [n.lower() for n in names]
        print(f"Pod cache refreshed with {len(names)} items")
        logger.debug("Refreshed pod cache with %d items", len(names))
    except Exception as e:
        print(f"WARNING: Failed to refresh pod cache: {str(e)}")
        logger.warning("Failed to refresh pod cache: %s", str(e))

def refresh_deployment_cache():
    """Refresh deployment cache with efficient query"""
    try:
        print("Refreshing deployment cache...")
        deployments = k8s_api.apps_v1.list_namespaced_deployment(
            namespace="default",
            timeout_seconds=5
        ).items
        names = [d.metadata.name for d in deployments]
        with cache_lock:
            deployment_search_cache["names"] = names
            deployment_search_cache["lower"] = [n.lower() for n in names]
        print(f"Deployment cache refreshed with {len(names)} items")
        logger.debug("Refreshed deployment cache with %d items", len(names))
    except Exception as e:
        print(f"WARNING: Failed to refresh deployment cache: {str(e)}")
        logger.warning("Failed to refresh deployment cache: %s", str(e))

# Start the cache updater when module loads
print("Initializing cache updater...")
start_cache_updater()
print("Cache updater initialized")

def search_pods(name_pattern, namespace="default"):
    """Optimized pod search using pre-cached data"""
    print(f"Searching pods with pattern: '{name_pattern}' in namespace: {namespace}")
    if namespace != "default":
        print("Using fallback search for non-default namespace")
        return _fallback_pod_search(name_pattern, namespace)
    
    name_lower = name_pattern.lower()
    
    with cache_lock:
        names = pod_search_cache["names"]
        lower_names = pod_search_cache["lower"]
    
    # Exact match (case-insensitive)
    try:
        idx = lower_names.index(name_lower)
        print(f"Found exact match: {names[idx]}")
        return [names[idx]]
    except ValueError:
        pass
    
    # Prefix matches
    prefix_matches = []
    for name, lower in zip(names, lower_names):
        if lower.startswith(name_lower):
            prefix_matches.append(name)
            if len(prefix_matches) >= 20:
                break
    
    if prefix_matches:
        print(f"Found {len(prefix_matches)} prefix matches")
        return prefix_matches[:20]
    
    # Partial matches
    partial_matches = [name for name, lower in zip(names, lower_names) 
                      if name_lower in lower][:20]
    print(f"Found {len(partial_matches)} partial matches")
    return partial_matches

def search_deployments(name_pattern, namespace="default"):
    """Optimized deployment search using pre-cached data"""
    print(f"Searching deployments with pattern: '{name_pattern}' in namespace: {namespace}")
    if namespace != "default":
        print("Using fallback search for non-default namespace")
        return _fallback_deployment_search(name_pattern, namespace)
    
    name_lower = name_pattern.lower()
    
    with cache_lock:
        names = deployment_search_cache["names"]
        lower_names = deployment_search_cache["lower"]
    
    # Exact match (case-insensitive)
    try:
        idx = lower_names.index(name_lower)
        print(f"Found exact match: {names[idx]}")
        return [names[idx]]
    except ValueError:
        pass
    
    # Prefix matches
    prefix_matches = []
    for name, lower in zip(names, lower_names):
        if lower.startswith(name_lower):
            prefix_matches.append(name)
            if len(prefix_matches) >= 10:
                break
    
    if prefix_matches:
        print(f"Found {len(prefix_matches)} prefix matches")
        return prefix_matches[:10]
    
    # Partial matches
    partial_matches = [name for name, lower in zip(names, lower_names) 
                      if name_lower in lower][:10]
    print(f"Found {len(partial_matches)} partial matches")
    return partial_matches

def _fallback_pod_search(name_pattern, namespace):
    """Fallback for non-default namespaces"""
    try:
        print(f"Running fallback pod search for namespace: {namespace}")
        pods = k8s_api.core_v1.list_namespaced_pod(namespace).items
        return _search_list([p.metadata.name for p in pods], name_pattern, 20)
    except Exception as e:
        print(f"ERROR in fallback pod search: {str(e)}")
        logger.error(f"Fallback pod search failed: {str(e)}")
        return []

def _fallback_deployment_search(name_pattern, namespace):
    """Fallback for non-default namespaces"""
    try:
        print(f"Running fallback deployment search for namespace: {namespace}")
        deployments = k8s_api.apps_v1.list_namespaced_deployment(namespace).items
        return _search_list([d.metadata.name for d in deployments], name_pattern, 10)
    except Exception as e:
        print(f"ERROR in fallback deployment search: {str(e)}")
        logger.error(f"Fallback deployment search failed: {str(e)}")
        return []

def _search_list(items, pattern, limit):
    """Generic search helper"""
    print(f"Running generic search on {len(items)} items with pattern: '{pattern}'")
    lower_items = [item.lower() for item in items]
    pattern_lower = pattern.lower()
    
    # Exact match
    try:
        idx = lower_items.index(pattern_lower)
        print("Found exact match")
        return [items[idx]]
    except ValueError:
        pass
    
    # Prefix matches
    prefix_matches = []
    for item, lower in zip(items, lower_items):
        if lower.startswith(pattern_lower):
            prefix_matches.append(item)
            if len(prefix_matches) >= limit:
                break
    
    if prefix_matches:
        print(f"Found {len(prefix_matches)} prefix matches")
        return prefix_matches
    
    # Partial matches
    partial_matches = [item for item, lower in zip(items, lower_items)
                     if pattern_lower in lower][:limit]
    print(f"Found {len(partial_matches)} partial matches")
    return partial_matches