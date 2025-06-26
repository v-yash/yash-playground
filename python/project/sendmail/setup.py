
import json
from setuptools import setup

kwargs = json.loads(
    """
{
    "name": "sendmail",
    "packages": ["sendmail"],
    "scripts": [ "bin/sendmail" ],
    "python_requires": ">=3.8",
    "author": "v-yash",
    "author_email": "email_id@email.com",
    "version": "1.0.1",
    "description": "Sendmail python library for sending mail else alerting on slack if mailing does not work",
    "install_requires": [
        "requests==2.32.3",
        "boto3>=1.35.87",
        "botocore>=1.35.87"
    ]
}
"""
)

setup(**kwargs)
