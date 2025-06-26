# Sendmail Replacement Package

This package provides a replacement for the traditional `sendmail` command. It integrates with Amazon Simple Email Service (SES) to send emails while maintaining compatibility with applications that use the `sendmail` command. The package can be used both as a command-line tool and as an importable Python module.

---

## Features
- **Dual Usage**: Can be used as a command-line tool (like traditional sendmail) or imported as a Python module
- **AWS SES Integration**: Sends emails using AWS SES via an assumed IAM role
- **Environment Variable Support**: Replaces placeholders like `${VARIABLE_NAME}` in email content with corresponding environment variables
- **Error Handling**: Provides detailed error messages and sends alerts to Slack in case of failures
- **Multiple Recipients**: Supports sending to multiple recipients (comma-separated in To field)
- **Flexible Installation**: Can be installed system-wide or in virtual environments

---

## Prerequisites

### AWS Setup
1. Ensure you have an IAM role in your SES account with the required permissions to send emails
2. Note the Role ARN and update the `ROLE_ARN` variable in the script

### Slack Webhook
1. Generate a Slack webhook URL for your channel
2. Update the `SLACK_WEBHOOK_URL` variable in the script

### Python Requirements
Python 3.8 or higher is required

---

## Installation

### Option 1: Install from source
```bash
pip install .
```

### Option 2: Build and install as PyPI package
1. First, build the package:
   ```bash
   python setup.py sdist bdist_wheel
   ```
2. The built package will be in the `dist/` directory. You can install it directly:
   ```bash
   pip install dist/sendmail-1.3.1.tar.gz
   ```
3. Or upload to your private PyPI repository:
   ```bash
   twine upload --repository-url <your-private-pypi-url> dist/*
   ```

This will:
1. Install the package and its dependencies (boto3, requests)
2. Place the executable script in your Python environment's bin directory

---

## Usage

### As a Command-Line Tool (sendmail replacement)

After installation, the script will be available as `sendmail` in your PATH:

```bash
echo -e "To: user@example.com\nSubject: Test Email\nFrom: sender@example.com\n\nThis is a test email body." | sendmail -vt
```

#### Input Format
- `To`: Recipient email address(es) - multiple addresses can be comma-separated
- `Subject`: Email subject
- `From`: Sender email address
- The email body starts after an empty line

#### Environment Variables
Placeholders like `${VARIABLE_NAME}` in email content will be replaced with corresponding environment variable values.

Example:
```bash
export EMAIL_RECIPIENT="recipient@example.com"
export Env="Production"
```

Content:
```bash
To: ${EMAIL_RECIPIENT}
Subject: [${Env}] Job Status
From: sender@example.com

Email body text.
```

### As a Python Module

You can import and use the sendmail functionality in your Python scripts:

```python
from sendmail import sendmail

headers = {
    "From": "sender@example.com",
    "To": "recipient1@example.com,recipient2@example.com",
    "Subject": "Test Email"
}
body = "This is the email body content."

# Send as plain text
sendmail.main(headers=headers, body=body, is_html=False)

# Or read from stdin-like object
import io
input_stream = io.StringIO("To: user@example.com\nSubject: Test\nFrom: sender@example.com\n\nBody")
sendmail.main()
```

---

## Error Handling
If the script encounters an error, it:
1. Prints the error message to the console
2. Sends an alert to the configured Slack webhook with details about the failure
3. Includes environment information (App Name, Cluster/Environment) in alerts

---

## Development

### Project Structure
```
sendmail/
├── bin/                # Contains executable script
├── sendmail/          # Package directory
│   └── sendmail.py    # Main implementation
├── setup.py           # Package configuration
└── README.md          # Documentation
```

### Building for Distribution
To build a PyPI-compatible package:
```bash
# Install build tools
pip install build wheel twine

# Build the package
python -m build

# The resulting packages will be in dist/
# sendmail-1.0.1.tar.gz   - Source distribution
# sendmail-1.0.1-py3-none-any.whl  - Wheel distribution
```

### Testing
1. Install the package in development mode:
   ```bash
   pip install -e .
   ```
2. Test command-line usage:
   ```bash
   echo -e "To: user@example.com\nSubject: Test\nFrom: sender@example.com\n\nBody" | sendmail -vt
   ```
3. Test module usage:
   ```python
   from sendmail import sendmail
   sendmail.main(...)
   ```

---

## Future Improvements
- Add support for HTML email content
- Implement retry logic for transient SES failures
- Add CC and BCC support
- Enhance configuration management (e.g., via config file)

---

For questions or assistance, please raise it in issues section of the repository.
```