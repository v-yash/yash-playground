import os
import json
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.signature import SignatureVerifier
from functools import wraps
from flask import request, abort
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

# Load roles configuration
with open('roles_config.json', 'r') as file:
    roles_config = json.load(file)

# Cache for user email lookups
user_email_cache = {}
CACHE_TTL = 3600

def verify_slack_request(request):
    """Verify Slack request signature"""
    logger.info("Verifying Slack request signature")
    print(f"Verifying Slack equest signature: {request.headers}")
    verifier = SignatureVerifier(os.environ['SLACK_SIGNING_SECRET'])
    if not verifier.is_valid_request(request.get_data(), request.headers):
        logger.warning("Invalid Slack request signature")
        print("Invalid Slack request signature")
        return False
    logger.info("Valid Slack request signature")
    print("Valid Slack request signature")
    return True

def get_user_email(user_id):
    """Get user email with TTL caching"""
    logger.info(f"Fetching email for user ID: {user_id}")
    print(f"Fetching email for user ID: {user_id}")
    if not isinstance(user_id, str) or not user_id.startswith('U'):
        logger.warning(f"Invalid user ID format: {user_id}")
        print(f"Invalid user ID format: {user_id}")
        return None
    
    # Check cache
    cache_entry = user_email_cache.get(user_id)
    if cache_entry:
        email, timestamp = cache_entry
        if datetime.now() - timestamp < timedelta(seconds=CACHE_TTL):
            return email
    
    # Fetch from API
    try:
        response = client.users_info(user=user_id)
        logger.debug(f"Full Slack API response: {response}")
        email = response['user']['profile']['email'].lower()
        print(f"Fetched email: {email}")
        user_email_cache[user_id] = (email, datetime.now())
        return email
    except Exception as e:
        logger.error(f"Error fetching user email: {str(e)}")
        print(f"Error fetching user email: {str(e)}")
        return None


def is_user_allowed(user_id):
    logger.info(f"Checking if user {user_id} is allowed")
    print(f"Checking if user {user_id} is allowed")
    
    user_email = get_user_email(user_id)
    if not user_email:
        logger.warning(f"Could not determine email for user {user_id}")
        print(f"Could not determine email for user {user_id}")
        return False
    
    allowed_emails = [email.lower() for email in roles_config.get("allowed_users", [])]
    is_allowed = user_email in allowed_emails
    
    logger.info(f"User {user_id} {'is' if is_allowed else 'is not'} allowed")
    print(f"User {user_id} {'is' if is_allowed else 'is not'} allowed")
    return is_allowed

def is_user_admin(user_id):
    logger.info(f"Checking if user {user_id} is an admin")
    print(f"Checking if user {user_id} is an admin")
    
    user_email = get_user_email(user_id)
    if not user_email:
        logger.warning(f"Could not determine email for user {user_id}")
        print(f"Could not determine email for user {user_id}")
        return False
    
    logger.info(f"User email resolved: {user_email}")
    print(f"User email resolved: {user_email}")
    logger.info(f"Admin emails list: {roles_config.get('admin_users', [])}")
    
    admin_emails = [email.lower() for email in roles_config.get("admin_users", [])]
    is_admin = user_email in admin_emails
    
    logger.info(f"User {user_id} {'is' if is_admin else 'is not'} an admin")
    return is_admin

def slack_auth_required(f):
    """Decorator for Slack endpoint authentication"""
    logger.info("Applying Slack authentication decorator")
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not verify_slack_request(request):
            abort(403, "Invalid request signature")
        return f(*args, **kwargs)
    return decorated_function