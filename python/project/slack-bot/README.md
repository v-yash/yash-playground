# devops-bot

# Kubernetes Slack Bot :robot_face:

A secure Slack bot for managing Kubernetes resources with approval workflows.  
*Currently supports basic operations - enhanced features coming soon!*

## :gear: Current Features

### :mag: **Basic Commands**
| Command     | Target Resource | Description                          | Example                     |
|-------------|-----------------|--------------------------------------|-----------------------------|
| `get`       | Pod/Deployment  | Get single resource or list matches  | `get pod/my-app`            |
| `describe`  | Pod             | Show key details of a pod            | `describe pod/my-app`       |
| `restart`   | Deployment      | Rollout restart a deployment         | `restart deployment/my-app` |

### :lock: Security
- User whitelisting via `roles_config.json`
- Kubernetes RBAC-limited service account
- Input sanitization for all commands

## :wrench: Setup

### Prerequisites
- Slack workspace with admin permissions
- Kubernetes cluster (v1.20+)
- Python 3.8+

### Installation
```bash
# Clone repo
git clone https://github.com/treebo-noss/devops-bot.git
cd devops-bot

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Fill in your Slack/K8s credentials

### Deployment

# Local testing
python app.py

# Production
gunicorn --bind 0.0.0.0:8080 app:app

:computer: Configuration
roles_config.json

{
  "allowed_users": ["xyz", "xyz"],
  "admin_users": ["xyz"]
}

Required Slack Scopes
app_mentions:read
chat:write
commands
files:write
users:read

:bulb: Usage
Invoke the bot with /jarvis slash command

Select operation from dropdown

Enter resource name (supports partial matching)

:shield: Safety Mechanisms
Command Validation: Blocks dangerous operations (delete, edit)

Output Limits: Auto-truncates large responses (>3000 chars)

Rate Limiting: 5 requests/minute per user

:roadmap: Coming Soon
Scale deployments

Read-only pod exec

Multi-cluster support

:ambulance: Troubleshooting
Error	Solution
We had some trouble connecting	Bot is processing - check your DMs
No matching resources	Verify resource exists in default namespace
Unauthorized	Request access in #k8s-support


# Kubernetes Slack Bot :robot_face:

## :triangular_ruler: Architecture Overview

### Component Diagram
```mermaid
flowchart TD
    A[Slack Workspace] -->|Slash Commands| B[Bot Server]
    B -->|Kubectl API| C[Kubernetes Cluster]
    C -->|Response| B
    B -->|Post Messages| A
    D[User] -->|Interacts| A
    B -->|Audit Logs| E[(Database)]

[Slack Server]
  │
  ├─ HTTPS Request → [Your Ingress (devops-bot.hotelsuperhero.com)]
  │                   │
  │                   ├─ TLS Termination
  │                   └─ Routes to Service:3001 → Pod:8080
  │
  └─ Headers:
      - X-Slack-Signature (Verified)
      - X-Slack-Request-Timestamp (Checked)
      - Authorization (Bot Token)

[Your Application]
  ├─ 1. Verify Slack Signature → Reject if invalid
  ├─ 2. Check User Allowlist → Reject if unauthorized
  └─ 3. Sanitize Commands → Reject malformed inputs


Endpoint Security Layers
Layer	Protection	Implementation
1. HTTPS Encryption	Prevents eavesdropping	Enforced by Ingress TLS (cert-manager)
2. Slack Signature Verification	Ensures only Slack can call your endpoint	verify_slack_request() checks X-Slack-Signature
3. Token Authentication	Validates Slack tokens	SLACK_BOT_TOKEN + SLACK_SIGNING_SECRET validation
4. User Allowlisting	Restricts bot access	is_user_allowed(user_id) checks roles_config.json
5. Input Sanitization	Prevents command injection	execute_safe_kubectl() validates commands


slack_handler.py
├── handle_slash_command()          # Initial command entry
├── handle_interaction()            # Main interaction handler
│   ├── validate_app_name()         # NEW: Add validation here
│   └── open_resource_selection()   # Modified to accept user_id
├── open_resource_selection()       # Now requires user_id parameter
├── handle_block_actions()          # Dynamic dropdown updates
└── execute_command()               # Final command execution