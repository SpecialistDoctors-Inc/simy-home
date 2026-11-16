"""Reviewed private S3/OAC hosting template. Does not change web or mail DNS."""
import re
from domain_verification import site_host
from publisher import ACCOUNT


def hosting_template(name, host, dns, *, consumer_role_arn, permissions_boundary_arn):
    if not re.fullmatch(r'hp-clinic-[0-9a-f]{20}', name) or site_host('https://' + host) != host:
        raise ValueError('invalid_hosting_identity')
    if (dns.get('status') != 'verified' or dns.get('host') != host
            or not re.fullmatch(r'Z[A-Z0-9]{5,32}', dns.get('hosted_zone_id', ''))
            or not (host == dns['domain'] or host.endswith('.' + dns['domain']))):
        raise ValueError('verified_route53_zone_required')
    if (not re.fullmatch('arn:aws:iam::' + ACCOUNT + r':role/[A-Za-z0-9+=,.@_/-]+', consumer_role_arn or '')
            or not re.fullmatch('arn:aws:iam::' + ACCOUNT + r':policy/[A-Za-z0-9+=,.@_/-]+', permissions_boundary_arn or '')):
        raise ValueError('same_account_runtime_and_boundary_required')
    resources = {
        'Certificate': {'Type': 'AWS::CertificateManager::Certificate', 'Properties': {
            'DomainName': host, 'ValidationMethod': 'DNS', 'DomainValidationOptions': [
                {'DomainName': host, 'HostedZoneId': dns['hosted_zone_id']}],
            'Tags': [{'Key': 'hp-control-managed', 'Value': 'true'}]}}
    }
    outputs = {}
    resources['DirectoryIndex'] = {'Type': 'AWS::CloudFront::Function', 'Properties': {
        'Name': name + '-index', 'AutoPublish': True,
        'FunctionConfig': {'Comment': 'Static directory index', 'Runtime': 'cloudfront-js-2.0'},
        'FunctionCode': "function handler(event){var r=event.request;if(r.uri.endsWith('/'))r.uri+='index.html';return r;}"}}
    for env, label in [('dev', 'Dev'), ('prod', 'Prod')]:
        bucket = name + '-' + ACCOUNT + '-' + env
        resources[label + 'Bucket'] = {'Type': 'AWS::S3::Bucket', 'DeletionPolicy': 'Retain',
            'UpdateReplacePolicy': 'Retain', 'Properties': {'BucketName': bucket,
            'VersioningConfiguration': {'Status': 'Enabled'},
            'OwnershipControls': {'Rules': [{'ObjectOwnership': 'BucketOwnerEnforced'}]},
            'PublicAccessBlockConfiguration': {'BlockPublicAcls': True, 'BlockPublicPolicy': True,
                'IgnorePublicAcls': True, 'RestrictPublicBuckets': True},
            'BucketEncryption': {'ServerSideEncryptionConfiguration': [{'ServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}]}}}
        resources[label + 'Access'] = {'Type': 'AWS::CloudFront::OriginAccessControl', 'Properties': {
            'OriginAccessControlConfig': {'Name': name + '-' + env, 'OriginAccessControlOriginType': 's3',
                'SigningBehavior': 'always', 'SigningProtocol': 'sigv4'}}}
        config = {'Enabled': True, 'IPV6Enabled': True, 'Comment': name + '-' + env, 'HttpVersion': 'http2and3',
            'PriceClass': 'PriceClass_200', 'DefaultRootObject': 'index.html',
            'Origins': [{'Id': 'site', 'DomainName': {'Fn::GetAtt': [label + 'Bucket', 'RegionalDomainName']},
                'OriginAccessControlId': {'Ref': label + 'Access'}, 'S3OriginConfig': {'OriginAccessIdentity': ''}}],
            'DefaultCacheBehavior': {'TargetOriginId': 'site', 'ViewerProtocolPolicy': 'redirect-to-https',
                'AllowedMethods': ['GET', 'HEAD', 'OPTIONS'], 'CachedMethods': ['GET', 'HEAD'],
                'Compress': True, 'MinTTL': 0, 'DefaultTTL': 0, 'MaxTTL': 86400,
                'ForwardedValues': {'QueryString': False, 'Cookies': {'Forward': 'none'}},
                'FunctionAssociations': [{'EventType': 'viewer-request', 'FunctionARN': {'Fn::GetAtt': ['DirectoryIndex', 'FunctionARN']}}]}}
        if env == 'prod':
            config.update(Aliases=[host], ViewerCertificate={'AcmCertificateArn': {'Ref': 'Certificate'},
                'SslSupportMethod': 'sni-only', 'MinimumProtocolVersion': 'TLSv1.2_2021'})
        else:
            config['ViewerCertificate'] = {'CloudFrontDefaultCertificate': True}
        resources[label + 'Distribution'] = {'Type': 'AWS::CloudFront::Distribution', 'Properties': {
            'DistributionConfig': config, 'Tags': [{'Key': 'hp-control-managed', 'Value': 'true'}]}}
        resources[label + 'Policy'] = {'Type': 'AWS::S3::BucketPolicy', 'Properties': {
            'Bucket': {'Ref': label + 'Bucket'}, 'PolicyDocument': {'Version': '2012-10-17', 'Statement': [{
                'Effect': 'Allow', 'Principal': {'Service': 'cloudfront.amazonaws.com'}, 'Action': 's3:GetObject',
                'Resource': {'Fn::Sub': '${' + label + 'Bucket.Arn}/*'},
                'Condition': {'StringEquals': {'AWS:SourceArn': {'Fn::Sub':
                    'arn:aws:cloudfront::${AWS::AccountId}:distribution/${' + label + 'Distribution}'}}}}]}}}
        outputs[label + 'Bucket'] = {'Value': {'Ref': label + 'Bucket'}}
        outputs[label + 'Distribution'] = {'Value': {'Ref': label + 'Distribution'}}
        statements = [
            {'Effect': 'Allow', 'Action': ['s3:ListBucket'], 'Resource': {'Fn::GetAtt': [label + 'Bucket', 'Arn']}},
            {'Effect': 'Allow', 'Action': ['s3:GetObject', 's3:PutObject', 's3:DeleteObject'],
             'Resource': {'Fn::Sub': '${' + label + 'Bucket.Arn}/*'}},
            {'Effect': 'Allow', 'Action': ['cloudfront:GetDistribution', 'cloudfront:GetDistributionConfig',
                'cloudfront:UpdateDistribution', 'cloudfront:CreateInvalidation', 'cloudfront:ListInvalidations',
                'cloudfront:GetInvalidation'], 'Resource': {'Fn::Sub':
                    'arn:aws:cloudfront::${AWS::AccountId}:distribution/${' + label + 'Distribution}'}}]
        if env == 'prod':
            statements.extend([
                {'Effect': 'Allow', 'Action': ['route53:ListResourceRecordSets'],
                 'Resource': 'arn:aws:route53:::hostedzone/' + dns['hosted_zone_id']},
                {'Effect': 'Allow', 'Action': ['route53:ChangeResourceRecordSets'],
                 'Resource': 'arn:aws:route53:::hostedzone/' + dns['hosted_zone_id'],
                 'Condition': {'ForAllValues:StringEquals': {
                     'route53:ChangeResourceRecordSetsNormalizedRecordNames': [host],
                     'route53:ChangeResourceRecordSetsRecordTypes': ['A', 'AAAA', 'CNAME'],
                     'route53:ChangeResourceRecordSetsActions': ['DELETE', 'CREATE']}}}])
        resources[label + 'Publisher'] = {'Type': 'AWS::IAM::Role', 'Properties': {
            'RoleName': name + '-publisher-' + env, 'PermissionsBoundary': permissions_boundary_arn,
            'AssumeRolePolicyDocument': {'Version': '2012-10-17', 'Statement': [{
                'Effect': 'Allow', 'Principal': {'AWS': consumer_role_arn}, 'Action': 'sts:AssumeRole'}]},
            'Policies': [{'PolicyName': 'isolated-site-publication', 'PolicyDocument': {
                'Version': '2012-10-17', 'Statement': statements}}]}}
        outputs[label + 'PublisherRole'] = {'Value': {'Fn::GetAtt': [label + 'Publisher', 'Arn']}}
    return {'AWSTemplateFormatVersion': '2010-09-09', 'Description': 'SIMY clinic isolated static environments',
            'Resources': resources, 'Outputs': outputs}
