#!/usr/bin/env python

import os
import unittest
import pytest
from email.message import Message

from pydpkg import Dsc
from pydpkg import DscMissingFileError
from pydpkg import DscBadSignatureError
from pydpkg import DscBadChecksumsError

from pgpy import PGPMessage


TEST_DSC_FILE = 'testdeb_0.0.0.dsc'
TEST_SIGNED_DSC_FILE = 'testdeb_0.0.0.dsc.asc'
TEST_BAD_DSC_FILE = 'testdeb_1.1.1-bad.dsc'
TEST_BAD_SIGNED_FILE = 'testdeb_1.1.1-bad.dsc.asc'
TEST_BAD_CHECKSUMS_FILE = 'testdeb_0.0.0-badchecksums.dsc'


class DscTest(unittest.TestCase):

    def setUp(self):
        self.dirn = os.path.dirname(__file__)
        goodfile = os.path.join(self.dirn, TEST_DSC_FILE)
        signed = os.path.join(self.dirn, TEST_SIGNED_DSC_FILE)
        badfile = os.path.join(self.dirn, TEST_BAD_DSC_FILE)
        badsigned = os.path.join(self.dirn, TEST_BAD_SIGNED_FILE)
        badchecksums = os.path.join(self.dirn, TEST_BAD_CHECKSUMS_FILE)
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

    def test_found_source_files(self):
        self.assertEqual(
            self.good.source_files,
            [os.path.join(self.dirn, 'testdeb_0.0.0.orig.tar.gz'),
             os.path.join(self.dirn, 'testdeb_0.0.0-1.debian.tar.xz'),
             os.path.join(self.dirn, 'testdeb_0.0.0.dsc')])

    def test_missing_files(self):
        self.assertEqual(True, self.good.all_files_present)
        self.assertEqual(False, self.bad.all_files_present)
        self.assertEqual(
            [os.path.join(self.dirn, 'testdeb_1.1.1.orig.tar.gz'),
             os.path.join(self.dirn, 'testdeb_1.1.1-1.debian.tar.xz')],
            self.bad.missing_files)
        with pytest.raises(DscMissingFileError):
            self.bad.validate()

    def test_pgp_validation(self):
        self.assertEqual(None, self.good.pgp_message)
        self.assertEqual(self.signed.source, 'testdeb')
        with pytest.raises(DscBadSignatureError):
            self.badsigned.source_files
        self.assertIsInstance(self.signed.pgp_message, PGPMessage)

    def test_parse_checksums(self):
        xz = os.path.join(self.dirn, 'testdeb_0.0.0-1.debian.tar.xz')
        gz = os.path.join(self.dirn, 'testdeb_0.0.0.orig.tar.gz')
        dsc = os.path.join(self.dirn, 'testdeb_0.0.0.dsc')
        self.assertEqual(
            self.good.checksums,
            {'md5': {xz: 'fc80e6e7f1c1a08b78a674aaee6c1548',
                     dsc: '893d13a2ef13f7409c9521e8ab1dbccb',
                     gz: '142ca7334ed1f70302b4504566e0c233'},
             'sha1': {xz: 'cb3474ff94053018957ebcf1d8a2b45f75dda449',
                      dsc: '80cd7b01014a269d445c63b037b885d6002cf533',
                      gz: 'f250ac0a426b31df24fc2c98050f4fab90e456cd'},
             'sha256': {
                 xz: '1ddb2a7336a99bc1d203f3ddb59f6fa2d298e90cb3e59cccbe0c84e359979858',
                 dsc: 'b5ad1591349eb48db65e6865be506ad7dbd21931902a71addee5b1db9ae1ac2a',
                 gz: 'aa57ba8f29840383f5a96c5c8f166a9e6da7a484151938643ce2618e82bfeea7'}})

    def test_checksum_validation(self):
        self.assertEqual(True, self.good.all_checksums_correct)
        self.assertEqual(False, self.badchecksums.all_checksums_correct)
        with pytest.raises(DscBadChecksumsError):
            self.badchecksums.validate()

    def test_message_internalization(self):
        self.maxDiff = None
        files = """142ca7334ed1f70302b4504566e0c233 280 testdeb_0.0.0.orig.tar.gz
 fc80e6e7f1c1a08b78a674aaee6c1548 232 testdeb_0.0.0-1.debian.tar.xz
 893d13a2ef13f7409c9521e8ab1dbccb 841 testdeb_0.0.0.dsc"""
        sha_1 = """f250ac0a426b31df24fc2c98050f4fab90e456cd 280 testdeb_0.0.0.orig.tar.gz
 cb3474ff94053018957ebcf1d8a2b45f75dda449 232 testdeb_0.0.0-1.debian.tar.xz
 80cd7b01014a269d445c63b037b885d6002cf533 841 testdeb_0.0.0.dsc"""
        sha_256 = """aa57ba8f29840383f5a96c5c8f166a9e6da7a484151938643ce2618e82bfeea7 280 testdeb_0.0.0.orig.tar.gz
 1ddb2a7336a99bc1d203f3ddb59f6fa2d298e90cb3e59cccbe0c84e359979858 232 testdeb_0.0.0-1.debian.tar.xz
 b5ad1591349eb48db65e6865be506ad7dbd21931902a71addee5b1db9ae1ac2a 841 testdeb_0.0.0.dsc"""
        self.assertEqual(
            # gah. the py2 and py3 email.Message implementations appear to
            # disagree on whether retreived multiline header strings will start
            # with a newline :( :( :(
            self.good.message['Files'].strip(),
            files)
        self.assertEqual(
            # ibid.
            self.good.message['checksums-sha1'].strip(),
            sha_1)
        self.assertEqual(
            # op. cit.
            self.good.message['checksums-sha256'].strip(),
            sha_256)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(DscTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
