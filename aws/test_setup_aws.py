import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish_engagement import make_event
from setup_aws import firehose_request, ident, names


class SetupAwsTests(unittest.TestCase):
    def test_names_are_scoped_to_prefix_account_region(self):
        n = names('sg-retail-customer-360', '123456789012', 'us-west-2')
        self.assertEqual(n['bucket'], 'sg-retail-customer-360-123456789012-us-west-2')
        self.assertEqual(n['storage_int'], 'SG_RETAIL_CUSTOMER_360_S3_INT')
        self.assertEqual(n['firehose_stream'], 'sg-retail-customer-360-engagement')

    def test_rejects_unsafe_identifiers(self):
        for bad in ['DB; DROP', 'a-b', '1abc', '']:
            with self.assertRaises(ValueError):
                ident(bad)

    def test_firehose_request_matches_aws_schema(self):
        import botocore.session
        from botocore.validate import validate_parameters
        n = names('sg-retail-customer-360', '123456789012', 'us-west-2')
        req = firehose_request(n, n['bucket'], 'arn:aws:iam::123456789012:role/sg-retail-customer-360-firehose-s3')
        model = botocore.session.get_session().get_service_model('firehose')
        validate_parameters(req, model.operation_model('CreateDeliveryStream').input_shape)
        dest = req['ExtendedS3DestinationConfiguration']
        self.assertEqual(dest['Prefix'], 'engagement/')
        self.assertFalse(dest['ErrorOutputPrefix'].startswith('engagement/'))

    def test_engagement_event_matches_pipe_columns(self):
        import random
        event = make_event(random.Random(7))
        self.assertEqual(set(event), {'cohort_id', 'event_ts', 'amount_sgd', 'response_minutes', 'status', 'sent_ms'})
        self.assertRegex(event['cohort_id'], r'^COH-00[0-4]\d$')
        self.assertIn(event['status'], ('ISSUE', 'OK'))


if __name__ == '__main__':
    unittest.main()
