from kafka.sasl.oauth import AbstractTokenProvider
from aws_msk_iam_sasl_signer import MSKAuthTokenProvider
import boto3

class MSKTokenProvider(AbstractTokenProvider):
    def __init__(self):
        self.region = boto3.session.Session().region_name

    def token(self):
        token, _ = MSKAuthTokenProvider.generate_auth_token(self.region)
        return token