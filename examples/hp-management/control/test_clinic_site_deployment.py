import copy
import unittest

from clinic_site_deployment import ACCOUNT, NotReady, deployment_block, outputs_from_terraform
from provision_site import validate
from publisher import config_sha256
import test_provision_site

PROD_HOST = 'www.clinic-a.example.jp'


def distribution(env, bucket, aliases=(), origin_path=''):
    dist_id = 'ECLINICA' + env.upper()
    return {'Distribution': {
        'Id': dist_id, 'ARN': 'arn:aws:cloudfront::%s:distribution/%s' % (ACCOUNT, dist_id),
        'DomainName': 'd%s.cloudfront.net' % env,
        'DistributionConfig': {
            'Aliases': {'Quantity': len(aliases), 'Items': list(aliases)},
            'Origins': {'Quantity': 1, 'Items': [{
                'Id': 'clinic-site-s3', 'DomainName': bucket + '.s3.ap-northeast-1.amazonaws.com',
                'OriginPath': origin_path, 'OriginAccessControlId': 'EOAC', 'S3OriginConfig': {'OriginAccessIdentity': ''}}]},
            'DefaultRootObject': 'index.html', 'Comment': env}}, 'ETag': 'E1'}


class FakeCloudFront:
    def __init__(self, items):
        self.items, self.calls = items, []

    def get_distribution(self, Id):
        self.calls.append(Id)
        return copy.deepcopy(self.items[Id])


class FakeS3:
    def __init__(self, keys):
        self.keys = keys

    def get_paginator(self, name):
        assert name == 'list_objects_v2'
        keys = self.keys

        class Paginator:
            def paginate(self, Bucket, ExpectedBucketOwner):
                assert ExpectedBucketOwner == ACCOUNT
                return [{'Contents': [{'Key': k} for k in keys[Bucket][:2]]},
                        {'Contents': [{'Key': k} for k in keys[Bucket][2:]]}]
        return Paginator()


class ClinicSiteDeploymentTest(unittest.TestCase):
    def setUp(self):
        self.buckets = {env: 'simy-hp-site-clinic-a-%s-%s' % (env, ACCOUNT) for env in ('dev', 'prod')}
        self.outputs = {
            'deployment': {'value': {env: {'bucket': b, 'distribution_id': 'ECLINICA' + env.upper(),
                                           'origin_id': 'clinic-site-s3', 'domain_name': 'd%s.cloudfront.net' % env}
                                     for env, b in self.buckets.items()}},
            'dev_url': {'value': 'https://ddev.cloudfront.net'},
            'prod_url': {'value': 'https://' + PROD_HOST},
            'prod_domain_attached': {'value': True}}
        self.items = {'ECLINICADEV': distribution('dev', self.buckets['dev']),
                      'ECLINICAPROD': distribution('prod', self.buckets['prod'], aliases=[PROD_HOST])}
        self.keys = {b: ['index.html', 'error.html', 'css/site.css']
                     for b in self.buckets.values()}

    def block(self):
        return deployment_block(outputs_from_terraform(self.outputs), FakeCloudFront(self.items), FakeS3(self.keys))

    def test_block_completes_a_binding_the_publisher_accepts(self):
        block = self.block()
        prod = block['deployment']['prod']
        self.assertEqual(prod['expected_config_sha256'],
                         config_sha256(self.items['ECLINICAPROD']['Distribution']['DistributionConfig'], 'clinic-site-s3'))
        self.assertEqual(prod['initial_file_paths'], ['css/site.css', 'error.html', 'index.html'])
        self.assertEqual(block['claim_target'], {env: {'bucket': b, 'distribution': 'ECLINICA' + env.upper()}
                                                 for env, b in self.buckets.items()})
        site = {**test_provision_site.ProvisionTest().site(), 'site_id': 'clinic-a',
                'dev_url': block['dev_url'], 'prod_url': block['prod_url'], 'deployment': block['deployment']}
        self.assertEqual(validate(site)['prod_url'], 'https://' + PROD_HOST)

    def test_prod_domain_must_be_attached_first(self):
        self.outputs['prod_domain_attached'] = {'value': False}
        with self.assertRaisesRegex(NotReady, 'attach the prod domain'):
            self.block()
        self.outputs['prod_domain_attached'] = {'value': True}
        self.items['ECLINICAPROD'] = distribution('prod', self.buckets['prod'])
        with self.assertRaisesRegex(NotReady, 'is not served'):
            self.block()

    def test_published_or_foreign_destinations_are_refused(self):
        self.items['ECLINICADEV'] = distribution('dev', self.buckets['dev'], origin_path='/releases/' + 'a' * 64)
        with self.assertRaisesRegex(NotReady, 'already published'):
            self.block()
        self.items['ECLINICADEV'] = distribution('dev', 'someone-else')
        with self.assertRaisesRegex(NotReady, 'private clinic-site bucket'):
            self.block()
        self.items['ECLINICADEV'] = distribution('dev', self.buckets['dev'])
        self.items['ECLINICADEV']['Distribution']['ARN'] = 'arn:aws:cloudfront::111111111111:distribution/ECLINICADEV'
        with self.assertRaisesRegex(NotReady, 'HP Control account'):
            self.block()

    def test_initial_copy_must_be_publishable(self):
        self.keys[self.buckets['prod']] = ['about.html']
        with self.assertRaisesRegex(NotReady, 'not publishable'):
            self.block()
        self.keys[self.buckets['prod']] = ['index.html', 'server.js']
        with self.assertRaisesRegex(NotReady, 'not publishable'):
            self.block()
        # releases/ belongs to the publisher, even for otherwise valid content.
        self.keys[self.buckets['prod']] = ['index.html', 'releases/2025/notice.pdf']
        with self.assertRaisesRegex(NotReady, 'releases/'):
            self.block()


if __name__ == '__main__':
    unittest.main()
