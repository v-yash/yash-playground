import os
import json
import logging
import datetime
from slack_sdk import WebClient
from flask import jsonify, Response
from jarvis.auth import is_user_allowed, is_user_admin
from slack_sdk.errors import SlackApiError
import threading
from jarvis.kubectl import execute_safe_kubectl, search_deployments, search_pods, k8s_api
from scripts.facets_prod_release_pause_resume import run_pause_release

logger = logging.getLogger(__name__)
client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
    
def handle_slash_command(form_data):
    print(f"\n=== Handling slash command ===")
    print(f"Received form data: {form_data}")
    try:
        user_id = form_data.get("user_id")
        trigger_id = form_data.get("trigger_id")
        channel_id = form_data.get("channel_id")
        is_admin = is_user_admin(user_id)
        print(f"User: {user_id}, Trigger ID: {trigger_id}, Channel: {channel_id}")
        
        if not is_user_allowed(user_id):
            print(f"⚠️ User {user_id} is not authorized")
            return jsonify({"response_type": "ephemeral", "text": "❌ Unauthorized"})
        
        if not trigger_id:
            print("⚠️ Missing trigger ID")
            return jsonify({
                "response_type": "ephemeral",
                "text": "⚠️ Missing trigger ID. Please try the command again."
            })
        
        response = {
            "response_type": "ephemeral",
            "text": "JARVIS on duty..!!",
            "replace_original": True
        }
        
        try:
            print("Opening initial modal...")
            open_initial_modal(trigger_id, channel_id, is_admin)
            print("✅ Modal opened successfully")
        except Exception as e:
            print(f"❌ Failed to open modal: {str(e)}")
            response["text"] = "⚠️ Failed to open command panel"
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ Slash command failed: {str(e)}")
        return jsonify({"response_type": "ephemeral", "text": "⚠️ Failed to process command"})

def process_command_async(payload):
    print(f"\n=== Processing command async ===")
    print(f"Payload received: {json.dumps(payload, indent=2)}")
    try:
        view = payload.get("view", {})
        values = view.get("state", {}).get("values", {})
        user_id = payload.get("user", {}).get("id", "unknown")
        metadata = json.loads(view.get("private_metadata", "{}"))
        channel_invoked = metadata.get("channel_id")
        channel_id = "channel_id"
        output = ""
        print(f"Processing for user: {user_id}, channel: {channel_invoked}")

        # Get user info for audit before executing commands
        print("Fetching user info...")
        try:
            user_info = client.users_info(user=user_id).get("user", {})
            user_name = user_info.get("real_name", "Unknown User")
            print(f"User identified: {user_name}")
        except Exception:
            user_name = "Unknown User"
            print("⚠️ Could not fetch user info")

        # Extract command details
        command_select = values.get("command_type", {}).get("command_select", {})
        command = command_select.get("selected_option", {}).get("value")
        print(f"Command selected: {command}")

        # Authorization checks
        if not is_user_allowed(user_id):
            print(f"❌ User {user_id} not authorized for any commands")
            send_slack_message(user_id, "❌ You are not authorized to use this bot.")
            return

        if command in ["scale", "exec"] and not is_user_admin(user_id):
            print(f"❌ User {user_id} not authorized for {command} command")
            send_slack_message(user_id, f"❌ You are not authorized to execute the '{command}' command.")
            return

        # Resource selection
        resource_select = values.get("resource_name", {}).get("resource_search", {})
        resource_name = resource_select.get("selected_option", {}).get("value")
        print(f"Resource selected: {resource_name}")

        # Validate command
        valid_commands = ["get", "describe", "restart", "scale", "exec", "pause", "resume"]
        if not command or command not in valid_commands:
            print(f"❌ Invalid command: {command}")
            send_slack_message(user_id, "❌ Invalid command")
            return

        if not resource_name and command not in ["pause", "resume"]:
            print("❌ No resource selected")
            send_slack_message(user_id, "❌ Please select a resource from the list")
            return

        try:
            resource_type = "deployment" if command in ["restart", "scale"] else "pod"
            print(f"Executing {command} on {resource_type}/{resource_name}")

            if command == "scale":
                try:
                    # Replica validation
                    replicas_block = values.get("replica_input", {}).get("replica_count", {})
                    replicas_str = replicas_block.get("value", "").strip()
                    print(f"Replica input: {replicas_str}")
                    
                    if not replicas_str:
                        print("❌ Missing replica count")
                        send_slack_message(user_id, "❌ Missing replica count")
                        return

                    try:
                        replicas = int(replicas_str)
                        print(f"Replica count: {replicas}")
                    except ValueError:
                        print("❌ Invalid replica number format")
                        send_slack_message(user_id, "❌ Must be a whole number")
                        return

                    if not (1 <= replicas <= 10):
                        print(f"❌ Replica count out of range: {replicas}")
                        send_slack_message(user_id, "❌ Replicas must be 1-10")
                        return

                    # HPA Check
                    try:
                        print(f"Checking HPA for {resource_name}")
                        hpa = k8s_api.autoscaling_v1.read_namespaced_horizontal_pod_autoscaler(
                            name=resource_name,
                            namespace="default"
                        )
                        if replicas > hpa.spec.max_replicas:
                            msg = f"Cannot exceed HPA max ({hpa.spec.max_replicas} replicas)"
                            print(f"❌ {msg}")
                            send_slack_message(user_id, f"❌ {msg}")
                            return
                        if replicas < hpa.spec.min_replicas:
                            msg = f"Cannot go below HPA min ({hpa.spec.min_replicas} replicas)"
                            print(f"❌ {msg}")
                            send_slack_message(user_id, f"❌ {msg}")
                            return
                    except Exception as e:
                        if getattr(e, 'status', None) != 404:
                            print(f"❌ HPA check failed: {str(e)}")
                            send_slack_message(user_id, "⚠️ HPA verification error")
                            return

                    # Execute scaling
                    cmd = f"scale deployment/{resource_name} --replicas={replicas}"
                    print(f"Executing: {cmd}")
                    output = execute_safe_kubectl(cmd)
                    print(f"Scale command output: {output}")

                    # Format messages for scale command
                    user_message = f":white_check_mark: *{command} {resource_type}/{resource_name}*\n{output}"
                    channel_message = f":white_check_mark: {command} {resource_type}/{resource_name}\nExecuted by {user_name}"

                except Exception as e:
                    print(f"❌ Scale command failed: {str(e)}")
                    send_slack_message(user_id, f"❌ Scale failed: {str(e)}")
                    return
            if command in ["pause", "resume"]:
                if not is_user_admin(user_id):
                    send_slack_message(user_id, "❌ Admin permission required!")
                    return

                cluster = "p-2621-aps1-01"
                try:
                    run_pause_release(
                        cluster_name=cluster,
                        pause_releases="true" if command == "pause" else "false"
                    )
                    msg = f"✅ Successfully {command}d releases on {cluster}"
                except Exception as e:
                    msg = f"❌ {command} failed: {str(e)}"
                
                send_slack_message(user_id, msg)
                if channel_id:
                    send_slack_message(channel_id, f"Releases {command}d by <@{user_id}>", True)
                return
            
            elif command == "exec":
                exec_block = values.get("exec_input", {}).get("exec_command", {})
                exec_command = exec_block.get("value", "").strip()
                print(f"Command to execute in pod: {exec_command}")
                
                if not exec_command:
                    print("❌ No command provided for exec")
                    send_slack_message(user_id, "❌ Please provide a command to execute in the pod")
                    return
                
                output = execute_command(command, resource_type, resource_name, exec_command)
                
                # Format messages for exec command
                user_message = (
                    f":white_check_mark: *Command executed in {resource_type}/{resource_name}*\n"
                    f"`{exec_command}`\n\n"
                    f"```{output}```"
                )
                channel_message = (
                    f":white_check_mark: Command executed in {resource_type}/{resource_name}\n"
                    f"Executed by {user_name}\n"
                    f"Command: `{exec_command}`"
                )

            else:
                # Non-scale, non-exec commands
                output = execute_command(command, resource_type, resource_name)
                print(f"Command output: {output[:200]}...")  # Truncate long output
                if not output:
                    output = "Command executed successfully (no output returned)"
                
                # Format messages for other commands
                user_message = f":white_check_mark: *{command} {resource_type}/{resource_name}*\n{output}"
                channel_message = f":white_check_mark: {command} {resource_type}/{resource_name}\nExecuted by {user_name}"

            # Send messages
            print(f"Sending DM to user {user_id}")
            send_slack_message(user_id, user_message)

            if channel_id and channel_id.startswith('C'):
                print(f"Posting to channel {channel_id}")
                try:
                    send_slack_message(channel_id, channel_message, is_channel_message=True)
                    print("✅ Channel message sent")
                except SlackApiError as e:
                    if e.response['error'] == 'not_in_channel':
                        print("⚠️ Bot not in channel - skipping channel message")
                    else:
                        print(f"❌ Channel post error: {str(e)}")
                except Exception as e:
                    print(f"❌ Channel message error: {str(e)}")
                    send_slack_message(user_id, "❌ Failed to post to channel")

            print(f"✅ Successfully processed {command} command")

        except Exception as e:
            print(f"❌ Command execution error: {str(e)}")
            send_slack_message(user_id, f"❌ Command failed: {str(e)}")

    except Exception as e:
        print(f"❌ Async processing failed: {str(e)}")
        send_slack_message(user_id, "⚠️ Command processing encountered an error")

def open_initial_modal(trigger_id, channel_id, is_admin):
    print(f"\n=== Opening initial modal ===")
    print(f"Trigger ID: {trigger_id}, Channel: {channel_id}")
    try:
        command_options = [
        {"text": {"type": "plain_text", "text": "Get"}, "value": "get"},
        {"text": {"type": "plain_text", "text": "Describe"}, "value": "describe"},
        {"text": {"type": "plain_text", "text": "Restart"}, "value": "restart"},
        ]
        
        if is_admin:
            command_options.extend([
                {"text": {"type": "plain_text", "text": "Scale (in dev)"}, "value": "scale"},
                {"text": {"type": "plain_text", "text": "Exec"}, "value": "exec"},
                {"text": {"type": "plain_text", "text": "Pause Release"}, "value": "pause"},
                {"text": {"type": "plain_text", "text": "Resume Release"}, "value": "resume"}
            ])

        view = {
            "type": "modal",
            "callback_id": "k8s_command",
            "title": {"type": "plain_text", "text": "Kubernetes Commander"},
            "submit": {"type": "plain_text", "text": "Execute"},
            "private_metadata": json.dumps({
                "channel_id": channel_id,
                "created_at": datetime.datetime.now().isoformat(),
                "command": "get",
                "namespace": "default",
                "is_admin": is_admin  # Store admin status in metadata
            }),
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*Namespace:* `default`"}
                },
                {
                    "block_id": "command_type",
                    "type": "input",
                    "element": {
                        "type": "radio_buttons",
                        "options": command_options,
                        "action_id": "command_select"
                    },
                    "label": {"type": "plain_text", "text": "Select command:"},
                    "dispatch_action": True
                },
                {
                    "block_id": "resource_name",
                    "type": "input",
                    "element": {
                        "type": "external_select",
                        "action_id": "resource_search",
                        "placeholder": {"type": "plain_text", "text": "Type at least 3 characters..."},
                        "min_query_length": 3
                    },
                    "label": {"type": "plain_text", "text": "Search resource:"}
                }
            ]
        }
        client.views_open(trigger_id=trigger_id, view=view)
        print("✅ Modal view sent successfully")
    except SlackApiError as e:
        print(f"❌ Modal open failed: {e.response['error']}")
        raise

def handle_options_request(payload):
    print(f"\n=== Handling options request ===")
    try:
        print(f"Payload: {json.dumps(payload, indent=2)}")
        view = payload.get("view", {})
        metadata = json.loads(view.get("private_metadata", "{}"))
        namespace = metadata.get("namespace", "default")
        command = metadata.get("command")
        print(f"Namespace: {namespace}, Command: {command}")

        # Fallback to checking view state values
        if not command:
            state_values = view.get("state", {}).get("values", {})
            command_block = state_values.get("command_type", {}).get("command_select", {})
            command = command_block.get("selected_option", {}).get("value")
            print(f"Fallback command: {command}")

        query = payload.get("value", "").strip().lower()
        print(f"Search query: '{query}'")
        
        # Determine resource type based on command
        if command in ["restart", "scale"]:
            print("Searching deployments...")
            resources = search_deployments(query)
        else:
            print("Searching pods...")
            resources = search_pods(query)

        print(f"Found {len(resources)} matching resources")
        return jsonify({
            "options": [{"text": {"type": "plain_text", "text": res}, "value": res} for res in resources[:100]]
        })
    except Exception as e:
        print(f"❌ Options request failed: {str(e)}")
        return jsonify({"options": []})

def handle_interaction(form_data):
    print(f"\n=== Handling interaction ===")
    print(f"Form data: {form_data}")
    try:
        payload_str = form_data.get("payload")
        if not payload_str:
            print("⚠️ Empty payload received")
            return jsonify({"response_type": "ephemeral", "text": "Empty request"})

        payload = json.loads(payload_str)
        print(f"Interaction type: {payload.get('type')}")

        if payload.get("type") == "block_actions":
            action = payload["actions"][0]
            print(f"Action ID: {action['action_id']}")
            # Modify the command_select handler section to:
            if action["action_id"] == "command_select":
                view = payload["view"]
                new_command = action["selected_option"]["value"]
                print(f"Command changed to: {new_command}")
                
                # Keep all blocks except conditional ones
                blocks = [b for b in view["blocks"] if b.get("block_id") not in [
                    "warning_block", "replica_input", "exec_input"]]
                
                # Remove resource selection for pause/resume commands
                if new_command in ["pause", "resume"]:
                    blocks = [b for b in blocks if b.get("block_id") != "resource_name"]

                if new_command == "restart":
                    print("Adding restart warning block")
                    warning_block = {
                        "type": "section",
                        "block_id": "warning_block",
                        "text": {
                            "type": "mrkdwn",
                            "text": ":warning: *You are restarting a pod in the production environment. Proceed with caution.*"
                        }
                    }
                    insert_index = next((i for i, b in enumerate(blocks) if b.get("block_id") == "command_type"), len(blocks)) + 1
                    blocks.insert(insert_index, warning_block)

                if new_command in ["pause", "resume"]:
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"⚠️ *You are about to {new_command} production releases!*"
                        }
                    })

                if new_command == "scale":
                    print("Adding replica input block")
                    blocks.append({
                        "type": "input",
                        "block_id": "replica_input",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "replica_count",
                            "placeholder": {"type": "plain_text", "text": "Enter number of replicas"}
                        },
                        "label": {"type": "plain_text", "text": "Replicas"}
                    })
                
                if new_command == "exec":
                    print("Adding user command input block")
                    blocks.append({
                        "type": "input",
                        "block_id": "exec_input",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "exec_command",
                            "placeholder": {"type": "plain_text", "text": "Enter the command to execute inside the pod"}
                        },
                        "label": {"type": "plain_text", "text": "Command to execute"}
                    })

                print("Updating modal view...")
                client.views_update(
                    view_id=view["id"],
                    hash=view["hash"],
                    view={
                        "type": "modal",
                        "callback_id": view["callback_id"],
                        "title": view["title"],
                        "blocks": blocks,
                        "private_metadata": json.dumps({
                            **json.loads(view["private_metadata"]),
                            "command": new_command
                        }),
                        "submit": view["submit"]
                    }
                )
                return Response(status=200)

        if payload.get("type") == "view_submission":
            print("Handling view submission")
            if not all(key in payload for key in ["user", "view"]):
                print("⚠️ Invalid payload structure")
                return jsonify({"response_action": "errors", "errors": {"_": "Invalid payload structure"}})
            
            print("Starting async processing...")
            threading.Thread(target=process_command_async, args=(payload,)).start()
            return Response(response=json.dumps({"response_action": "clear"}), status=200, mimetype='application/json')

        return Response(status=200)
    
    except json.JSONDecodeError:
        print("❌ Invalid JSON payload")
        return jsonify({"response_type": "ephemeral", "text": "Invalid payload format"})
    except Exception as e:
        print(f"❌ Interaction handler failed: {str(e)}")
        return jsonify({"response_type": "ephemeral", "text": "Processing started (check logs for errors)"})
        
def execute_command(command, resource_type, resource_name, exec_command=None):
    print(f"\n=== Executing command ===")
    print(f"Command: {command}, Resource: {resource_type}/{resource_name}")
    try:
        if command == "get":
            resource_type = {"pod": "pods", "deployment": "deployments"}.get(resource_type, resource_type)
            cmd = f"get {resource_type} --field-selector metadata.name={resource_name}"
        elif command == "restart":
            cmd = f"rollout restart deployment/{resource_name}"
        elif command == "describe":
            cmd = f"describe {resource_type}/{resource_name}"
        elif command == "exec":
            if not exec_command:
                raise ValueError("No command provided to execute in the pod")
            cmd = f"exec {resource_type}/{resource_name} -- {exec_command}"
        elif command == "scale":
            raise ValueError("Scale command should be handled directly in process_command_async.")
        else:
            raise ValueError(f"Unsupported command: {command}")

        print(f"Executing: {cmd}")
        result = execute_safe_kubectl(cmd)
        print(f"Command executed successfully")
        return result

    except Exception as e:
        print(f"❌ Command execution failed: {str(e)}")
        return f"Error: {str(e)}"

def send_slack_message(channel, text, is_channel_message=False):
    print(f"\n=== Sending Slack message ===")
    print(f"Channel: {channel}, Is channel: {is_channel_message}")
    print(f"Message content: {text[:200]}...")  # Truncate long messages
    try:
        if is_channel_message and channel.startswith('C'):
            try:
                print("Posting to channel...")
                return client.chat_postMessage(channel=channel, text=text, mrkdwn=True)
            except SlackApiError as e:
                if e.response['error'] == 'not_in_channel':
                    print("⚠️ Bot not in channel - skipping")
                    return None
                print(f"❌ Channel post error: {str(e)}")
                raise
        
        print("Sending direct message...")
        return client.chat_postMessage(channel=channel, text=text, mrkdwn=True)
        
    except Exception as e:
        print(f"❌ Failed to send Slack message: {str(e)}")
        return None