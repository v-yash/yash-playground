import requests
import json
import sys
import os
import logging
import base64

CONTROL_PLANE = "url"
STACK = "stack_name"
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class ClusterPauseResume:

    def __init__(self, cluster_name, environment, pause_releases, user, facets_auth_token):
        self.url = f"https://{CONTROL_PLANE}"
        self.headers = {
            'Authorization': f'Basic {facets_auth_token}',
            'Content-Type': 'application/json'
        }
        self.cluster = dict()
        self.stack_name = STACK
        self.cluster_name = cluster_name
        self.environment = environment
        self.pause_releases = pause_releases.lower() == 'true'
        self.user_name = user

    def get_cluster_from_stack(self):
        clusters = self.get_clusters()
        for cluster in clusters:
            if cluster['name'] == self.cluster_name:
                self.cluster = cluster
                return
        raise Exception(f"Cluster '{self.cluster_name}' not found.")

    def get_clusters(self):
        url = f"{self.url}/cc-ui/v1/stacks/{self.stack_name}/clusters"
        response = self.get(url)
        return response

    def get(self, url):
        response = requests.get(url, headers=self.headers)
        return self.check_api_response(response)

    def post(self, url, payload):
        try:
            response = requests.post(url, headers=self.headers, data=json.dumps(payload))
            print(f"API response status: {response.status_code}")
            result = self.check_api_response(response)
            print("API result:", result)
            return result
        except Exception as e:
            print("POST request failed:", e)

    def check_api_response(self, response):
        if response.status_code == 200:
            try:
                return response.json()
            except ValueError:
                # Empty or invalid JSON body, treat as success
                return {"message": "Success", "status_code": 200}
        else:
            raise Exception(f"API Error: {response.status_code} - {response.text}")

    def send_notification(self, cluster_name, pause_releases, user_name):
        slack_url = os.environ.get("SLACK_WEBHOOK_URL")
        status = "PAUSED" if pause_releases else "RESUMED"
        message = f"Cluster `{cluster_name}` releases has been `{status}` by `{user_name}`"
        slack_data = {'text': message}
        headers = {'Content-Type': "application/json"}
        response = requests.post(slack_url, data=json.dumps(slack_data), headers=headers)
        if response.status_code != 200:
            raise Exception(response.status_code, response.text)

    def execute_pause_resume(self):
        self.get_cluster_from_stack()
        cluster_id = self.cluster["id"]
        payload = {
            "clusterId": cluster_id,
            "pauseReleases": self.pause_releases
        }
        pause_resume_url = f"{self.url}/cc-ui/v1/clusters/{cluster_id}/pause-release"
        print(f"{'Pausing' if self.pause_releases else 'Resuming'} releases for cluster {self.cluster_name}...")
        self.post(pause_resume_url, payload)
        self.send_notification(self.cluster_name, self.pause_releases, self.user_name)


def run_pause_release(cluster_name, pause_releases, user="jarvis", environment="production"):
    auth_token = os.environ.get("FACETS_AUTH_TOKEN")
    if not auth_token:
        raise Exception("FACETS_AUTH_TOKEN is not set in environment variables.")
    
    facets_auth_token = base64.b64encode(auth_token.encode()).decode()

    controller = ClusterPauseResume(cluster_name, environment, pause_releases, user, facets_auth_token)
    controller.execute_pause_resume()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python facets_prod_release_pause_resume.py <cluster_name> <pause_releases>")
        sys.exit(1)

    cluster_name = sys.argv[1]
    pause_releases = sys.argv[2]

    run_pause_release(cluster_name, pause_releases)
