#!/usr/bin/env python3
"""Tell a Payment Link clinic that its operator-prepared homepage is ready.

Without --apply this only reads the subscription, intake, registration and the
deployed claim targets and prints what is missing. With --apply it invokes the
HP Control API Lambda directly, which claims the site for the clinic's verified
sign-in mailbox and emails that mailbox once (see clinic_ready.py).
"""
import argparse
import json

from clinic_ready import readiness

ACCOUNT = '209300895845'
REGION = 'ap-northeast-1'
FUNCTIONS = {'live': ('simy-hp-control', 'simy-hp-control-api'),
             'acceptance': ('simy-hp-control-acceptance', 'simy-hp-control-acceptance-api')}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--subscription-id', required=True, help='Stripe subscription (sub_...) of the purchase.')
    p.add_argument('--environment', choices=sorted(FUNCTIONS), default='live')
    p.add_argument('--apply', action='store_true', help='Claim the site and send the ready mail.')
    a = p.parse_args()
    import boto3
    from store import DynamoStore
    session = boto3.Session(region_name=REGION)
    if session.client('sts').get_caller_identity()['Account'] != ACCOUNT:
        raise SystemExit('wrong AWS account')
    table, function = FUNCTIONS[a.environment]
    lambda_client = session.client('lambda')
    environment = lambda_client.get_function_configuration(FunctionName=function)['Environment']['Variables']
    claim_targets = json.loads(environment.get('HP_SITE_CLAIM_TARGETS', '{}'))
    report = readiness(DynamoStore(table, session.client('dynamodb')), a.subscription_id, claim_targets)
    print(json.dumps({'check': report, 'mail_configured': bool(environment.get('HP_EMAIL_LOGIN_FROM'))},
                     ensure_ascii=False))
    if not a.apply:
        return
    response = lambda_client.invoke(FunctionName=function, InvocationType='RequestResponse', Payload=json.dumps(
        {'hp_operator_task': 'clinic_ready', 'subscription_id': a.subscription_id}).encode())
    print(response['Payload'].read().decode())
    if response.get('FunctionError'):
        raise SystemExit('lambda error')


if __name__ == '__main__':
    main()
