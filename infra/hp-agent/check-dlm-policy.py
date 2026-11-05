#!/usr/bin/env python3
"""Read-only AWS IAM regression for a rendered DLM policy before apply.

Accept the JSON policy emitted by Terraform, never a credential file. The IAM
simulator verifies resource matching; a real scheduled snapshot and restore
remain required to establish runtime acceptance.
"""
import argparse
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--account', required=True)
    parser.add_argument('--region', required=True)
    parser.add_argument('--volume-id', required=True)
    args = parser.parse_args()
    policy = json.loads(args.policy.read_text())
    actual = json.loads(subprocess.check_output(['aws', 'sts', 'get-caller-identity']))
    if actual['Account'] != args.account:
        raise ValueError('AWS account mismatch')
    volume = f'arn:aws:ec2:{args.region}:{args.account}:volume/'
    snapshot = f'arn:aws:ec2:{args.region}::snapshot/snap-0123456789abcdef0'
    tags = [{'ContextKeyName': f'aws:ResourceTag/{name}',
             'ContextKeyValues': [value], 'ContextKeyType': 'string'}
            for name, value in [('Project', 'hp-agent'), ('Purpose', 'hp-agent-state')]]
    wrong_purpose = [tags[0], {**tags[1], 'ContextKeyValues': ['unrelated']}]
    creating = [{'ContextKeyName': 'ec2:CreateAction',
                 'ContextKeyValues': ['CreateSnapshot'], 'ContextKeyType': 'string'}]
    cases = [
        ('create-selected-volume', 'ec2:CreateSnapshot', volume + args.volume_id, [], 'allowed'),
        ('create-snapshot-resource', 'ec2:CreateSnapshot', snapshot, [], 'allowed'),
        ('deny-unrelated-volume', 'ec2:CreateSnapshot', volume + 'vol-00000000000000000', [], 'implicitDeny'),
        ('delete-owned-tagged-snapshot', 'ec2:DeleteSnapshot', snapshot, tags, 'allowed'),
        ('deny-delete-untagged-snapshot', 'ec2:DeleteSnapshot', snapshot, [], 'implicitDeny'),
        ('deny-delete-wrong-purpose', 'ec2:DeleteSnapshot', snapshot, wrong_purpose, 'implicitDeny'),
        ('tag-new-snapshot', 'ec2:CreateTags', snapshot, creating, 'allowed'),
        ('deny-tag-existing-snapshot', 'ec2:CreateTags', snapshot, [], 'implicitDeny'),
    ]
    proof = []
    for name, action, resource, context, expected in cases:
        request = {'PolicyInputList': [json.dumps(policy)], 'ActionNames': [action],
                   'ResourceArns': [resource], 'ContextEntries': context}
        result = json.loads(subprocess.check_output([
            'aws', '--region', args.region, 'iam', 'simulate-custom-policy',
            '--cli-input-json', json.dumps(request)]))
        rows = result['EvaluationResults']
        if len(rows) != 1 or rows[0]['EvalResourceName'] != resource:
            raise ValueError(f'{name}: unexpected simulation result')
        decision = rows[0]['EvalDecision']
        proof.append({'case': name, 'decision': decision, 'expected': expected})
        if decision != expected:
            print(json.dumps(proof))
            raise SystemExit(f'{name}: policy regression')
    print(json.dumps({'account': args.account, 'checks': proof, 'passed': True}))


if __name__ == '__main__':
    main()
