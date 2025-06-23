import argparse
from kubernetes import client, config
from kubernetes.client.rest import ApiException

def scale_down_deployments(exclude_namespaces=None, exclude_deployments=None):
    if exclude_namespaces is None:
        exclude_namespaces = []
    if exclude_deployments is None:
        exclude_deployments = []
    
    config.load_kube_config()
    apps_v1 = client.AppsV1Api()
    
    print("Starting cluster scale-down operation...")
    
    try:
        deployments = apps_v1.list_deployment_for_all_namespaces().items
    except ApiException as e:
        print(f"Failed to list deployments: {e}")
        return
    
    scaled_count = 0
    skipped_count = 0
    
    for deploy in deployments:
        ns = deploy.metadata.namespace
        name = deploy.metadata.name
        current_replicas = deploy.spec.replicas or 0
        
        # Check if deployment should be excluded
        if ns in exclude_namespaces or name in exclude_deployments or current_replicas == 0:
            print(f"Skipping {ns}/{name} (current replicas: {current_replicas})")
            skipped_count += 1
            continue
        
        # Prepare patch to set replicas to 0
        patch = {"spec": {"replicas": 0}}
        
        try:
            apps_v1.patch_namespaced_deployment(
                name=name,
                namespace=ns,
                body=patch
            )
            print(f"Scaled {ns}/{name} from {current_replicas} to 0")
            scaled_count += 1
        except ApiException as e:
            print(f"Error scaling {ns}/{name}: {e}")
    
    print(f"\nScale-down summary:")
    print(f" - Total deployments processed: {len(deployments)}")
    print(f" - Successfully scaled: {scaled_count}")
    print(f" - Skipped: {skipped_count}")
    print("\nNote: Worker nodes will be terminated by the cluster autoscaler once all pods are terminated.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scale down all deployments in an EKS cluster')
    parser.add_argument('--exclude-ns', nargs='+', help='Namespaces to exclude', default=[])
    parser.add_argument('--exclude-deploy', nargs='+', help='Deployment names to exclude', default=[])
    
    args = parser.parse_args()
    
    scale_down_deployments(
        exclude_namespaces=args.exclude_ns,
        exclude_deployments=args.exclude_deploy
    )

# Basic scale-down
#python scale_down_eks.py

# Scale-down excluding specific namespaces and deployments
#python scale_down_eks.py --exclude-ns kube-system monitoring --exclude-deploy critical-app