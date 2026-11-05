import unittest

import dhcp_client

# This test checks if the dhcp client package is imported and can be used.
class PackageImportTests(unittest.TestCase):
    def test_package_is_importable(self):
        self.assertEqual(dhcp_client.__name__, "dhcp_client")


if __name__ == "__main__":
    unittest.main()
