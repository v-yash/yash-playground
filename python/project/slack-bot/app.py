from flask import Flask, request, jsonify, Response
import os
import logging
from jarvis.auth import verify_slack_request, slack_auth_required
from jarvis.slack_handler import handle_slash_command, handle_interaction

app = Flask(__name__)

# Initialize logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

@app.route("/slack/command", methods=["POST"])
@slack_auth_required
def slack_command():
    try:
        return handle_slash_command(request.form)
    except Exception as e:
        logger.error(f"Slash command failed: {str(e)}", exc_info=True)
        return jsonify({"response_type": "ephemeral", "text": "⚠️ Command processing failed"}), 200

@app.route("/slack/interactions", methods=["POST"])
@slack_auth_required
def slack_interactions():
    if request.content_length > 100000:  # 100KB
        return jsonify({"response_type": "ephemeral", "text": "Payload too large"}), 413
    try:
        return handle_interaction(request.form)
    except Exception as e:
        logger.error(f"Interaction failed: {str(e)}", exc_info=True)
        return jsonify({"response_type": "ephemeral", "text": "⚠️ Interaction processing failed"}), 200

@app.route("/health")
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route("/slack/events", methods=["POST"])
def slack_events():
    # Required for Options Load URL
    if request.json.get("type") == "url_verification":
        return jsonify({"challenge": request.json.get("challenge")})
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)