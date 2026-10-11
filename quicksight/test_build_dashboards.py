"""Offline contract tests. These do not certify rendered dashboards or Q answers."""
import unittest
from unittest.mock import Mock
from build_dashboards import build_requests, validate_requests, apply_requests, wait_dashboard

ACCOUNT = '123456789012'
BASE = f'arn:aws:quicksight:us-west-2:{ACCOUNT}'

class DashboardTests(unittest.TestCase):
    def requests(self, **overrides):
        arguments = dict(account=ACCOUNT, region='us-west-2', principal=BASE + ':user/default/test',
                         source_arn=BASE + ':datasource/test', database='TEST_EVENTS', prefix='test')
        arguments.update(overrides)
        return build_requests(**arguments)

    def test_aws_schema(self):
        validate_requests(self.requests())

    def test_explicit_visuals_and_dataset_bindings(self):
        requests = self.requests()
        sheet = requests['dashboard']['Definition']['Sheets'][0]
        self.assertEqual(len(sheet['Visuals']), 5)
        self.assertEqual(len(requests['datasets']), 4)
        self.assertIn('ML.CHURN_RISK_SCORES', str(requests['datasets']))
        self.assertIn('RAW.LIVE_ENGAGEMENT', str(requests['datasets']))
        layout_ids = {e['ElementId'] for e in sheet['Layouts'][0]['Configuration']['GridLayout']['Elements']}
        visual_ids = {next(iter(v.values()))['VisualId'] for v in sheet['Visuals']}
        self.assertEqual(layout_ids, visual_ids)
        self.assertIn('EVENT_COUNT', str(requests['datasets']))
        self.assertNotIn('SELECT *', str(requests))
        self.assertNotIn('{{', str(requests))

    def test_reject_identifiers_and_cross_account_resources(self):
        for overrides in [dict(database='DB; DROP TABLE X'), dict(prefix='../escape'),
                          dict(principal=BASE.replace(ACCOUNT, '999999999999') + ':user/default/test')]:
            with self.assertRaises(ValueError):
                self.requests(**overrides)

    def test_account_mismatch_prevents_writes(self):
        session = Mock()
        session.client.return_value.get_caller_identity.return_value = {'Account': '999999999999'}
        with self.assertRaisesRegex(RuntimeError, 'identity mismatch'):
            apply_requests(session, self.requests())
        session.client.assert_called_once_with('sts')

    def test_failed_version_does_not_pass(self):
        client = Mock()
        client.describe_dashboard.return_value = {'Dashboard': {'Version': {'Status': 'CREATION_FAILED'}}}
        with self.assertRaisesRegex(RuntimeError, 'failed'):
            wait_dashboard(client, ACCOUNT, 'test-dashboard', 1)

    def test_successful_version(self):
        client = Mock()
        client.describe_dashboard.return_value = {'Dashboard': {'Version': {'Status': 'CREATION_SUCCESSFUL'}}}
        wait_dashboard(client, ACCOUNT, 'test-dashboard', 1)
        client.describe_dashboard.assert_called_once_with(AwsAccountId=ACCOUNT, DashboardId='test-dashboard', VersionNumber=1)

if __name__ == '__main__':
    unittest.main()
