import os
import json
import logging
import re
from slack_sdk import WebClient
from flask import jsonify, Response
from jarvis.auth import is_user_allowed
from slack_sdk.errors import SlackApiError
import threading
from jarvis.kubectl import get_deployments, get_pods, execute_safe_kubectl, search_deployments, search_pods


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

def validate_app_name(app_name):
    if not app_name or len(app_name) < 2:
        raise ValueError("App name must be at least 2 characters")
    if not re.match(r'^[a-zA-Z0-9-]*$', app_name):
        raise ValueError("App name contains invalid characters")
    
def handle_slash_command(form_data):
    try:
        user_id = form_data.get("user_id")
        trigger_id = form_data.get("trigger_id")
        
        if not is_user_allowed(user_id):
            return jsonify({"response_type": "ephemeral", "text": "❌ Unauthorized"})
        
        if not trigger_id:
            return jsonify({
                "response_type": "ephemeral",
                "text": "⚠️ Missing trigger ID. Please try the command again."
            })
        
        open_initial_modal(trigger_id)
        return jsonify()  # Empty 200 response for slash commands
        
    except Exception as e:
        logger.error(f"Slash command failed: {str(e)}")
        return jsonify({"response_type": "ephemeral", "text": "⚠️ Failed to process command"})

def process_command_async(payload):
    """Process command in background with proper error handling"""
    try:
        view = payload.get("view", {})
        values = view.get("state", {}).get("values", {})
        user_id = payload.get("user", {}).get("id", "unknown")
        
        # Extract command details
        command_select = values.get("command_type", {}).get("command_select", {})
        command = command_select.get("selected_option", {}).get("value")
        app_name = values.get("app_name", {}).get("app_name_input", {}).get("value", "").strip()

        # Validate command
        if not command or command not in ["get", "describe", "restart", "scale"]:
            send_slack_message(user_id, "❌ Invalid command")
            return

        # Validate resource name
        if not app_name or len(app_name) < 2:
            send_slack_message(user_id, "❌ Resource name must be at least 2 characters")
            return

        # Find matching resources
        if command == "restart":
            resources = search_deployments(app_name)
            resource_type = "deployment"
        else:
            resources = search_pods(app_name)
            resource_type = "pod"

        # Handle results
        if not resources:
            send_slack_message(user_id, "❌ No matching resources found")
        elif len(resources) > 1:
            resource_list = "\n".join(resources[:10])  # Limit to 10 items
            send_slack_message(
                user_id,
                f"⚠️ Multiple matches ({len(resources)} found):\n```{resource_list}```\n"
                "Please refine your search"
            )
        else:  # Single match
            resource_name = resources[0]
            try:
                output = execute_command(command, resource_type, resource_name)
                if command == "describe":
                    # Prettify describe output
                    output = f"📋 *{resource_type}/{resource_name}*\n```{output[:3000]}...```" \
                            if len(output) > 3000 else f"📋 *{resource_type}/{resource_name}*\n```{output}```"
                
                send_slack_message("user_id", f"✅ *{command} {resource_type}/{resource_name}*\n{output}")
            except Exception as e:
                send_slack_message(user_id, f"❌ Command failed: {str(e)}")
                logger.error(f"Command execution error: {str(e)}", exc_info=True)

    except Exception as e:
        logger.error(f"Async processing failed: {str(e)}", exc_info=True)
        try:
            send_slack_message(user_id, "⚠️ Command processing encountered an error")
        except:
            pass  # Prevent infinite error loop

def open_initial_modal(trigger_id):
    view = {
        "type": "modal",
        "callback_id": "k8s_command",
        "title": {"type": "plain_text", "text": "Kubernetes Commander"},
        "submit": {"type": "plain_text", "text": "Execute"}, 
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Namespace:* `default`"}
            },
            {
                "block_id": "command_type",
                "type": "section",
                "text": {"type": "mrkdwn", "text": "Select command:"},
                "accessory": {
                    "type": "static_select",
                    "action_id": "command_select",
                    "options": [
                        {"text": {"type": "plain_text", "text": "get"}, "value": "get"},
                        {"text": {"type": "plain_text", "text": "describe"}, "value": "describe"},
                        {"text": {"type": "plain_text", "text": "restart"}, "value": "restart"},
                        #{"text": "scale", "value": "scale"}
                    ]
                }
            },
            {
                "block_id": "app_name",
                "type": "input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "app_name_input",
                    "placeholder": {"type": "plain_text", "text": "e.g. crs-app (exact match)"}
                },
                "label": {"type": "plain_text", "text": "Enter resource name:"}
            }
        ]
    }
    client.views_open(trigger_id=trigger_id, view=view)

def handle_interaction(form_data):
    """Handle initial interaction with immediate response to Slack"""
    try:
        payload_str = form_data.get("payload")
        if not payload_str:
            return jsonify({"response_type": "ephemeral", "text": "Empty request"})

        payload = json.loads(payload_str)
        
        if payload.get("type") == "view_submission":
            # Validate minimal required fields exist
            if not all(key in payload for key in ["user", "view"]):
                return jsonify({"response_action": "errors", "errors": {"_": "Invalid payload structure"}})
            
            # Immediate acknowledgement
            response = Response(
                response=json.dumps({"response_action": "clear"}),
                status=200,
                mimetype='application/json'
            )
            
            # Start async processing
            threading.Thread(target=process_command_async, args=(payload,)).start()
            
            return response

        return Response(status=200)
    
    except json.JSONDecodeError:
        return jsonify({"response_type": "ephemeral", "text": "Invalid payload format"})
    except Exception as e:
        logger.error(f"Interaction handler failed: {str(e)}", exc_info=True)
        return jsonify({"response_type": "ephemeral", "text": "Processing started (check logs for errors)"})
        
def execute_command(command, resource_type, resource_name):
    """Execute the actual kubectl command with validation"""
    try:
        if command == "get":
            resource_type = {
                "pod": "pods",
                "deployment": "deployments"
            }.get(resource_type, resource_type)
            cmd = f"get {resource_type} --field-selector metadata.name={resource_name}"
        elif command == "restart":
            cmd = f"rollout restart deployment/{resource_name}"
        elif command == "describe":
            cmd = f"describe {resource_type}/{resource_name}"
        # elif command == "scale":
        #     if not resource_name.isdigit():
        #         raise ValueError("Replicas must be a number")
        #     cmd = f"scale deployment/{resource_name} --replicas={value}"
        else:
            raise ValueError(f"Unsupported command: {command}")
            
        return execute_safe_kubectl(cmd)
    except Exception as e:
        logger.error(f"Command execution failed: {str(e)}")
        return f"Error: {str(e)}"

def handle_resource_execution(payload):
    """Handle final command execution from resource selection"""
    try:
        view = payload.get("view", {})
        values = view.get("state", {}).get("values", {})
        metadata = json.loads(view.get("private_metadata", "{}"))
        
        # Validate metadata
        command = metadata.get("command")
        app_name = metadata.get("app_name")
        if not command:
            raise ValueError("Missing command in metadata")

        # Validate resource selection
        resource_select = values.get("resource_select", {}).get("resource_select", {})
        resource = resource_select.get("selected_option", {}).get("value")
        if not resource:
            return jsonify({
                "response_action": "errors",
                "errors": {"resource_select": "Please select a resource"}
            })

        user_id = payload.get("user", {}).get("id", "unknown")
        logger.info(f"Executing {command} on {resource}")

        # Format command based on type
        if command == "restart":
            if not resource.startswith("deployment/"):
                resource = f"deployment/{resource}"
            cmd = f"kubectl rollout restart {resource}"
        else:
            if not resource.startswith("pod/"):
                resource = f"pod/{resource}"
            cmd = f"kubectl {command} {resource}"

        # Execute and respond
        output = execute_safe_kubectl(cmd)
        send_slack_message(
            user_id,
            f"✅ *Command Executed*\n`{cmd}`\n```\n{output}\n```"
        )
        return jsonify({"response_action": "clear"})

    except Exception as e:
        error_msg = f"❌ *Command Failed*\n`{cmd}`\nError: {str(e)}"
        send_slack_message(user_id, error_msg)
        return jsonify({"response_action": "clear"})

def send_slack_message(channel, text):
    """Helper function for consistent messaging with file fallback"""
    try:
        # Send as file if content is too large
        if len(text) > 3000:
            try:
                response = client.files_upload_v2(
                    channel=channel,
                    content=text,
                    title="Command Output",
                    filename="output.txt"
                )
                return response
            except SlackApiError as e:
                logger.error(f"Slack API error during file upload: {e.response['error']}")
                # Fallback to message if file upload fails
                return client.chat_postMessage(
                    channel=channel,
                    text=f"⚠️ Command output too large. Error uploading file: {e.response['error']}",
                    mrkdwn=True
                )
        else:
            return client.chat_postMessage(
                channel=channel,
                text=text,
                mrkdwn=True
            )
    except SlackApiError as e:
        logger.error(f"Slack API error: {e.response['error']}")
        return None
    except Exception as e:
        logger.error(f"Failed to send Slack message: {str(e)}")
        return None

def build_resource_selection_view(command, app_name, user_id):
    logger.debug(f"Building view for command: {command}, app: {app_name}")
    resources = search_deployments(app_name) if command == "restart" else search_pods(app_name)
    resource_type = "deployments" if command == "restart" else "pods"
    
    view = {
        "type": "modal",
        "callback_id": "k8s_resource_select",
        "title": {
            "type": "plain_text",
            "text": "Select Resource",
            "emoji": True
        },
        "submit": {
            "type": "plain_text",
            "text": "Execute",
            "emoji": True
        },
        "private_metadata": json.dumps({
            "command": command,
            "app_name": app_name
        }),
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Found {len(resources)} {resource_type} matching `{app_name}`",
                    "verbatim": False
                }
            },
            {
                "block_id": "resource_select",
                "type": "input",
                "label": {
                    "type": "plain_text",
                    "text": "Select resource:",
                    "emoji": True
                },
                "element": {
                    "type": "static_select",
                    "action_id": "resource_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Choose a resource",
                        "emoji": True
                    },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": r[:75],  # Ensure max 75 chars
                                "emoji": True
                            },
                            "value": r[:200]  # Max 200 chars for value
                        } for r in resources
                    ] or [  # Fallback for empty list
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "No resources found",
                                "emoji": True
                            },
                            "value": "none"
                        }
                    ],
                    "initial_option": (
                        {
                            "text": {
                                "type": "plain_text",
                                "text": resources[0][:75],
                                "emoji": True
                            },
                            "value": resources[0][:200]
                        } if resources else None
                    )
                }
            }
        ]
    }

    if not resources:
        logger.warning("No resources found for selection")

    logger.debug(f"Final view structure: {json.dumps(view, indent=2)}")
    return view

def update_resource_dropdown(payload):
    """Update resource dropdown based on selected command"""
    try:
        selected_command = payload["actions"][0]["selected_option"]["value"]
        view_id = payload["view"]["id"]
        current_view = payload["view"]
        
        # Get appropriate resources
        resources = get_deployments("default") if selected_command == "restart" else get_pods("default")
        
        # Update only the relevant block while preserving other fields
        updated_blocks = []
        for block in current_view["blocks"]:
            if block["block_id"] == "resource_name":
                updated_blocks.append({
                    "block_id": "resource_name",
                    "type": "input",
                    "label": {"type": "plain_text", "text": "Select resource:"},
                    "element": {
                        "type": "static_select",
                        "action_id": "resource_select",
                        "options": [
                            {"text": {"type": "plain_text", "text": r}, "value": r}
                            for r in resources or ["No resources found"]
                        ]
                    }
                })
            else:
                updated_blocks.append(block)
        
        client.views_update(
            view_id=view_id,
            view={
                "type": "modal",
                "callback_id": current_view["callback_id"],
                "title": current_view["title"],
                "submit": current_view["submit"],
                "blocks": updated_blocks
            }
        )
        return Response(status=200)
    except Exception as e:
        logger.error(f"Dropdown update failed: {str(e)}")
        return jsonify({"response_type": "ephemeral", "text": "⚠️ Failed to update resources"})

def handle_block_actions(payload):
    actions = payload.get("actions", [])
    action_id = actions[0]["action_id"]
    user_id = payload["user"]["id"]
    view_id = payload["view"]["id"]
    state_values = payload["view"]["state"]["values"]

    selected_namespace = state_values["namespace_select_block"]["namespace_select"]["selected_option"]["value"]
    
    # Optional: handle other interactions like command/resource type changes
    if action_id in ["namespace_select", "command_select", "resource_select"]:
        # Dynamically fetch pods for selected namespace
        pods = get_pods(selected_namespace)
        pod_options = [
            {
                "text": {"type": "plain_text", "text": pod},
                "value": pod
            } for pod in pods
        ]

        # Update modal with new resource name dropdown options
        updated_blocks = payload["view"]["blocks"]
        for block in updated_blocks:
            if block["block_id"] == "resource_name_input":
                block["accessory"]["options"] = pod_options

        # Push updated modal
        client.views_update(
            view_id=view_id,
            hash=payload["view"]["hash"],
            view={
                **payload["view"],
                "blocks": updated_blocks
            }
        )

    return jsonify()

def handle_modal_submission(payload):
    try:
        values = payload["view"]["state"]["values"]
        user_id = payload["user"]["id"]
        
        command = values["command_type"]["command_select"]["selected_option"]["value"]
        resource = values["resource_name"]["resource_select"]["selected_option"]["value"]
        
        # Build command
        if command == "restart":
            cmd = f"kubectl rollout restart deployment/{resource}"
        else:
            cmd = f"kubectl {command} {resource}"
        
        # Execute and respond
        output = execute_safe_kubectl(cmd)
        client.chat_postMessage(
            channel=user_id,
            text=f"Command: `{cmd}`\n```\n{output}\n```"
        )
        
        return jsonify({"response_action": "clear"})
        
    except Exception as e:
        logger.error(f"Command failed: {str(e)}")
        return jsonify({
            "response_action": "errors",
            "errors": {"resource_name": f"Failed: {str(e)}"}
        })

def build_edit_confirmation(resource, patch):
    return {
        "type": "modal",
        "title": {"type": "plain_text", "text": "Confirm Edit"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*You're about to edit:* `{resource}`\n*Changes:*\n```{patch}```"
                }
            }
        ],
        "submit": {"type": "plain_text", "text": "Confirm"}
    }