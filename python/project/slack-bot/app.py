from flask import Flask, request, jsonify
import logging, json
import os
from apscheduler.schedulers.background import BackgroundScheduler
from jarvis.auth import slack_auth_required
from jarvis.slack_handler import handle_slash_command, handle_interaction, handle_options_request
from scripts.facets_prod_release_pause_resume import run_pause_release

app = Flask(__name__)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@app.before_request
def log_request():
    """Log all incoming requests"""
    logger.info(
        "Incoming request",
        extra={
            'method': request.method,
            'path': request.path,
            'content_length': request.content_length
        }
    )

@app.route("/slack/command", methods=["POST"])
@slack_auth_required
def slack_command():
    try:
        logger.debug("Handling slash command")
        return handle_slash_command(request.form)
    except Exception as e:
        logger.error("Slash command processing failed", exc_info=True)
        return jsonify({
            "response_type": "ephemeral",
            "text": "⚠️ Command processing failed"
        }), 200

@app.route("/slack/interactions", methods=["POST"])
@slack_auth_required
def slack_interactions():
    if request.content_length > 100000:  # 100KB
        logger.warning("Payload too large", extra={'size': request.content_length})
        return jsonify({
            "response_type": "ephemeral",
            "text": "Payload too large"
        }), 413
    
    try:
        logger.debug("Handling interaction")
        return handle_interaction(request.form)
    except Exception as e:
        logger.error("Interaction processing failed", exc_info=True)
        return jsonify({
            "response_type": "ephemeral",
            "text": "⚠️ Interaction processing failed"
        }), 200

@app.route("/health")
def health_check():
    logger.debug("Health check requested")
    return jsonify({
        "status": "healthy",
        "components": {
            "scheduler": "active" if app.config.get('scheduler') else "inactive"
        }
    }), 200

@app.route("/slack/options", methods=["POST"])
@slack_auth_required
def slack_options():
    try:
        payload = json.loads(request.form["payload"])
        logger.debug("Handling options request")
        return handle_options_request(payload)
    except Exception as e:
        logger.error("Options request failed", exc_info=True)
        return jsonify({"options": []})

def scheduled_pause():
    try:
        logger.info("Running scheduled pause_release job")
        run_pause_release(
            cluster_name="cluster_name_placeholder",  # Replace with actual cluster name
            pause_releases="true"
        )
        logger.info("pause_release completed")
    except Exception as e:
        logger.error("Scheduled pause job failed", exc_info=True)

def scheduled_resume():
    try:
        logger.info("Running scheduled resume_release job")
        run_pause_release(
            cluster_name="cluster_name_placeholder",  # Replace with actual cluster name
            pause_releases="false"
        )
        logger.info("resume_release completed")
    except Exception as e:
        logger.error("Scheduled resume job failed", exc_info=True)

def schedule_jobs():
    scheduler = BackgroundScheduler(timezone='Asia/Kolkata')

    scheduler.add_job(
        scheduled_resume,
        trigger='cron',
        day_of_week='mon',
        hour=5,  # 5 AM IST
        minute=0
    )

    scheduler.add_job(
        scheduled_pause,
        trigger='cron',
        day_of_week='mon',
        hour=9,  # 9 AM IST
        minute=0
    )

    scheduler.add_job(
        scheduled_resume,
        trigger='cron',
        day_of_week='mon',
        hour=22, # 10 PM IST
        minute=0
    )

    scheduler.add_job(
        scheduled_pause,
        trigger='cron',
        day_of_week='tue',
        hour=2, # 2 AM IST
        minute=0
    )

    scheduler.add_job(
        scheduled_resume,
        trigger='cron',
        day_of_week='thu',
        hour=5,  # 5 AM IST
        minute=0
    )

    scheduler.add_job(
        scheduled_pause,
        trigger='cron',
        day_of_week='thu',
        hour=9,  # 9 AM IST
        minute=0
    )

    scheduler.add_job(
        scheduled_resume,
        trigger='cron',
        day_of_week='thu',
        hour=22, # 10 PM IST
        minute=0
    )

    scheduler.add_job(
        scheduled_pause,
        trigger='cron',
        day_of_week='fri',
        hour=2, # 2 AM IST
        minute=0
    )

    scheduler.start()
    app.config['scheduler'] = scheduler
    logger.info("Scheduled pause/resume jobs")

schedule_jobs()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)