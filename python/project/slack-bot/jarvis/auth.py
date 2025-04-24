import os
import json
import logging
from slack_sdk.signature import SignatureVerifier
from functools import wraps
from flask import request, abort

logger = logging.getLogger(__name__)

# Load allowed users
with open('roles_config.json', 'r') as file:
    roles_config = json.load(file)

def verify_slack_request(request):
    """Verify Slack request signature"""
    verifier = SignatureVerifier(os.environ['SLACK_SIGNING_SECRET'])
    if not verifier.is_valid_request(request.get_data(), request.headers):
        logger.warning("Invalid Slack request signature")
        return False
    return True

def is_user_allowed(user_id):
    """Check if user is authorized with input validation"""
    if not isinstance(user_id, str) or not user_id.startswith('U'):
        logger.warning(f"Invalid user_id format: {user_id}")
        return False
    return user_id in roles_config.get("allowed_users", [])

def slack_auth_required(f):
    """Decorator for Slack endpoint authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not verify_slack_request(request):
            abort(403, "Invalid request signature")
        return f(*args, **kwargs)
    return decorated_function