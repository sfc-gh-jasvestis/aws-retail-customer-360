"""Offline guard tests; no Snowflake session or cloud writes."""
import unittest
from unittest.mock import Mock
from run_core import validate_target, run

class CoreSafetyTests(unittest.TestCase):
    def test_live_namespace_rejected(self):
        with self.assertRaises(ValueError):
            validate_target('RETAIL_ANALYTICS', 'TEST_WH')

    def test_injected_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_target('SINGAPORE_RETAIL_CUSTOMER_360_TEST', 'WH;DROP DATABASE X')

    def test_wrong_account_stops_before_writes(self):
        connection = Mock()
        cursor = connection.cursor.return_value
        cursor.fetchone.return_value = ('OTHER', 'WRONG', 'PUBLIC.AWS_US_WEST_2')
        with self.assertRaisesRegex(RuntimeError, 'identity mismatch'):
            run(connection, 'SINGAPORE_RETAIL_CUSTOMER_360_TEST', 'TEST_WH', 'ABC12345')
        self.assertEqual(cursor.execute.call_count, 1)
        connection.close.assert_called_once()

    def test_large_warehouse_stops_before_writes(self):
        connection = Mock()
        cursor = connection.cursor.return_value
        cursor.fetchone.return_value = ('DEMO', 'ABC12345', 'PUBLIC.AWS_US_WEST_2')
        cursor.description = [('name',), ('size',), ('auto_suspend',)]
        cursor.fetchall.return_value = [('TEST_WH', 'Large', 60)]
        with self.assertRaisesRegex(RuntimeError, 'X-Small'):
            run(connection, 'SINGAPORE_RETAIL_CUSTOMER_360_TEST', 'TEST_WH', 'ABC12345')
        self.assertEqual(cursor.execute.call_count, 2)

if __name__ == '__main__':
    unittest.main()
