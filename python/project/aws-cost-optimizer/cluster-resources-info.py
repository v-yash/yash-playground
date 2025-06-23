from kubernetes import client, config
from datetime import datetime
import pytz
import openpyxl
from openpyxl.styles import Font

def get_deployments_data():
    config.load_kube_config()

    apps_v1 = client.AppsV1Api()
    hpa_api = client.AutoscalingV1Api()

    deployments = apps_v1.list_namespaced_deployment(namespace="default").items
    hpas = {h.metadata.name: h for h in hpa_api.list_namespaced_horizontal_pod_autoscaler("default").items}

    ist = pytz.timezone('Asia/Kolkata')
    timestamp = datetime.now(ist).strftime("%d-%b-%Y %H:%M:%S IST")

    data = []
    for d in deployments:
        name = d.metadata.name
        pod_labels = d.spec.template.metadata.labels or {}

        pod_size = pod_labels.get("podSize", "N/A")
        strategy = pod_labels.get("resourceAllocationStrategy", "N/A")

        min_replicas = hpas.get(name).spec.min_replicas if name in hpas else d.spec.replicas
        max_replicas = hpas.get(name).spec.max_replicas if name in hpas else d.spec.replicas

        current_replicas = d.status.replicas or 0
        status = "Enabled" if current_replicas > 0 else "Disabled"

        data.append([
            name,
            pod_size,
            strategy,
            max_replicas,
            min_replicas,
            status,
            timestamp
        ])
    return data

def save_to_excel(data, filename="k8s_deployments.xlsx"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Deployments"

    headers = ["Application_Name", "Size", "Size_Type", "Max_Replica", "Min_Replica", "Status", "Last_Modified"]
    ws.append(headers)

    for cell in ws[1]:
        cell.font = Font(bold=True)

    for row in data:
        ws.append(row)

    wb.save(filename)
    print(f"✅ Data written to: {filename}")

if __name__ == "__main__":
    deployments_data = get_deployments_data()
    save_to_excel(deployments_data)
