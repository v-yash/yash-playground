#!/usr/bin/env python3

import boto3
from botocore.exceptions import ClientError
import sys
import re
import os
import requests

# Constants for IAM role and Slack webhook URL
ROLE_ARN = "arn:aws:iam::<aws_account_id>:role/<role_name>" # Replace with your actual IAM role ARN
SLACK_WEBHOOK_URL = "slack_webhook_url"  # Replace with your actual Slack webhook URL
MAX_CONTENT_LENGTH = 1000  # Limit for Slack message content

def parse_email_content():
    headers = {}
    body_lines = []
    is_body = False

    # Check if input is provided via stdin
    input_source = sys.stdin if not sys.stdin.isatty() else None
    if input_source is None:
        print("Error: No input provided. Use '<' to pipe a file or provide input via stdin.")
        sys.exit(1)

    # Read and split input into headers and body
    for line in input_source:
        if is_body:
            body_lines.append(line)
        elif line.strip() == "":
            is_body = True
        else:
            key, _, value = line.partition(":")
            headers[key.strip()] = value.strip()

    # Replace environment variables in headers and body
    for key, value in headers.items():
        headers[key] = re.sub(r"\$\{(\w+)\}", lambda m: os.environ.get(m.group(1), ""), value)
    body = "".join(body_lines)
    body = re.sub(r"\$\{(\w+)\}", lambda m: os.environ.get(m.group(1), ""), body)

    return headers, body

def send_slack_alert(message, email_content=None):
    app_name = os.environ.get("APP_NAME") or os.environ.get("HOSTNAME", "Unknown App")

    cluster = (
        os.environ.get("CLUSTER_IDENTIFIER") or
        os.environ.get("APP_ENV") or
        os.environ.get("ENV") or
        os.environ.get("ENVIRONMENT", "Unknown Cluster")
    )

    # Truncate email content if it exceeds the maximum allowed length
    if email_content and len(email_content) > MAX_CONTENT_LENGTH:
        email_content = email_content[:MAX_CONTENT_LENGTH] + "...(truncated)"

    # Prepare the payload for Slack webhook
    payload = {
        "text": (
            f"*Sendmail Failed*: `{message}`\n"
            f"*App Name:* {app_name}\n"
            f"*Environment:* {cluster}\n"
            f"*Email Content:* ```{email_content}```"
        )
    }
    try:
        # Send POST request to Slack webhook
        response = requests.post(SLACK_WEBHOOK_URL, json=payload)
        if response.status_code != 200:
            print(f"Slack alert failed with status code {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Error sending Slack alert: {e}")

def send_email(sender, recipient_list, subject, body_text, is_html):
    sts_client = boto3.client('sts')
    # Assume the specified IAM role to get temporary credentials
    assumed_role = sts_client.assume_role(
        RoleArn=ROLE_ARN,
        RoleSessionName="SESSession"
    )
    credentials = assumed_role['Credentials']

    # Create an SES client using temporary credentials
    ses_client = boto3.client(
        'ses',
        region_name='eu-west-1',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken']
    )
    try:
        # Send email via AWS SES
        if is_html:
            body_dict = {'Html': {'Charset': "UTF-8", 'Data': body_text}}
        else:
            body_dict = {'Text': {'Charset': "UTF-8", 'Data': body_text}}

        response = ses_client.send_email(
            Destination={'ToAddresses': recipient_list},  # Pass the list of recipients
            Message={
                'Body': body_dict,
                'Subject': {'Charset': "UTF-8", 'Data': subject},
            },
            Source=sender,
        )
    except ClientError as e:
        # Construct email content with headers and body for Slack alert
        email_content = f"To: {', '.join(recipient_list)}\nSubject: {subject}\nFrom: {sender}\n\n{body_text}"
        error_message = f"SES Error: {e.response['Error']['Message']}"
        print(error_message)
        send_slack_alert(error_message, email_content)
        sys.exit(1)
    except Exception as e:
        # Handle unexpected errors
        email_content = f"To: {', '.join(recipient_list)}\nSubject: {subject}\nFrom: {sender}\n\n{body_text}"
        error_message = f"Unexpected Error: {e}"
        print(error_message)
        send_slack_alert(error_message, email_content)
        sys.exit(1)
    else:
        # Print success message if email is sent successfully
        print("Email sent successfully! Message ID:", response['MessageId'])

def main(headers=None, body=None, is_html=False):
    if headers and body:
        # Programmatic call with parameters
        sender = headers.get("From")
        recipients = headers.get("To")  # Can contain multiple email addresses separated by commas
        subject = headers.get("Subject")

        recipient_list = [email.strip() for email in recipients.split(",") if email.strip()]

        send_email(sender, recipient_list, subject, body, is_html)
    else:
        # Command-line call with stdin
        headers, body = parse_email_content()

        sender = headers.get("From")
        recipients = headers.get("To")  # Can contain multiple email addresses separated by commas
        subject = headers.get("Subject")

        recipient_list = [email.strip() for email in recipients.split(",") if email.strip()]

        send_email(sender, recipient_list, subject, body, is_html)

# if __name__ == "__main__":
#     main()
