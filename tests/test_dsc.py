#!/usr/bin/env python

import os
import unittest
import pytest
from email.message import Message

from pydpkg import Dsc, DscMissingFileError, DscBadSignatureError, DscBadChecksumsError
from pgpy import PGPMessage


TEST_DSC_FILE = 'testdeb_0.0.0.dsc'
TEST_SIGNED_DSC_FILE = 'testdeb_0.0.0.dsc.asc'
TEST_BAD_DSC_FILE = 'testdeb_1.1.1-bad.dsc'
TEST_BAD_SIGNED_FILE = 'testdeb_1.1.1-bad.dsc.asc'
TEST_BAD_CHECKSUMS_FILE = 'testdeb_0.0.0-badchecksums.dsc'


class DscTest(unittest.TestCase):
    def setUp(self):
        goodfile = os.path.join(os.path.dirname(__file__), TEST_DSC_FILE)
        signed = os.path.join(os.path.dirname(__file__), TEST_SIGNED_DSC_FILE)
        badfile = os.path.join(os.path.dirname(__file__), TEST_BAD_DSC_FILE)
        badsigned = os.path.join(os.path.dirname(__file__), TEST_BAD_SIGNED_FILE)
        badchecksums = os.path.join(os.path.dirname(__file__), TEST_BAD_CHECKSUMS_FILE)
        self.good = Dsc(goodfile)
        self.signed = Dsc(signed)
        self.bad = Dsc(badfile)
        self.badsigned = Dsc(badsigned)
        self.badchecksums = Dsc(badchecksums)

    def test_get_message_headers(self):
        self.assertEqual(self.good.source, 'testdeb')
        self.assertEqual(self.good.SOURCE, 'testdeb')
        self.assertEqual(self.good['source'], 'testdeb')
        self.assertEqual(self.good['SOURCE'], 'testdeb')
        self.assertEqual(self.good.get('source'), 'testdeb')
        self.assertEqual(self.good.get('SOURCE'), 'testdeb')
        self.assertEqual(self.good.get('nonexistent'), None)
        self.assertEqual(self.good.get('nonexistent', 'foo'), 'foo')

    def test_attr_munging(self):
        self.assertEqual(self.good['package-list'], 'testdeb')
        self.assertEqual(self.good.package_list, 'testdeb')

    def test_missing_header(self):
        self.assertRaises(KeyError, self.good.__getitem__, 'xyzzy')
        self.assertRaises(AttributeError, self.good.__getattr__, 'xyzzy')

    def test_message(self):
        self.assertIsInstance(self.good.message, type(Message()))

    def test_found_files(self):
        self.assertEqual(
            self.good.files,
            [os.path.join(os.path.dirname(__file__),
                          'testdeb_0.0.0.orig.tar.gz'),
             os.path.join(os.path.dirname(__file__),
                          'testdeb_0.0.0-1.debian.tar.xz')]
        )

    def test_missing_files(self):
        self.assertEqual(True, self.good.all_files_present)
        self.assertEqual(False, self.bad.all_files_present)
        self.assertEqual(
            [os.path.join(os.path.dirname(__file__),
                          'testdeb_1.1.1.orig.tar.gz'),
             os.path.join(os.path.dirname(__file__),
                          'testdeb_1.1.1-1.debian.tar.xz')],
            self.bad.missing_files)
        with pytest.raises(DscMissingFileError):
            self.bad.validate()

    def test_pgp_validation(self):
        self.assertEqual(None, self.good.pgp_message)
        self.assertEqual(self.signed.source, 'testdeb')
        with pytest.raises(DscBadSignatureError):
            self.badsigned.files
        self.assertIsInstance(self.signed.pgp_message, PGPMessage)

    def test_checksum_validation(self):
        self.assertEqual(True, self.good.all_checksums_correct)
        self.assertEqual(False, self.badchecksums.all_checksums_correct)
        with pytest.raises(DscBadChecksumsError):
            self.badchecksums.validate()


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(DscTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
