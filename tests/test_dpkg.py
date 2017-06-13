#!/usr/bin/env python

import os
import unittest
from email.message import Message

from pydpkg import Dpkg, DpkgVersionError


TEST_DPKG_FILE = 'testdeb_1:0.0.0-test_all.deb'


class DpkgTest(unittest.TestCase):
    def setUp(self):
        dpkgfile = os.path.join(os.path.dirname(__file__), TEST_DPKG_FILE)
        self.dpkg = Dpkg(dpkgfile)

    def test_get_versions(self):
        self.assertEqual(self.dpkg.epoch, 1)
        self.assertEqual(self.dpkg.upstream_version, '0.0.0')
        self.assertEqual(self.dpkg.debian_revision, 'test')

    def test_get_message_headers(self):
        self.assertEqual(self.dpkg.package, 'testdeb')
        self.assertEqual(self.dpkg.PACKAGE, 'testdeb')
        self.assertEqual(self.dpkg['package'], 'testdeb')
        self.assertEqual(self.dpkg['PACKAGE'], 'testdeb')
        self.assertEqual(self.dpkg.get('package'), 'testdeb')
        self.assertEqual(self.dpkg.get('PACKAGE'), 'testdeb')
        self.assertEqual(self.dpkg.get('nonexistent'), None)
        self.assertEqual(self.dpkg.get('nonexistent', 'foo'), 'foo')

    def test_missing_header(self):
        self.assertRaises(KeyError, self.dpkg.__getitem__, 'xyzzy')
        self.assertRaises(AttributeError, self.dpkg.__getattr__, 'xyzzy')

    def test_message(self):
        self.assertIsInstance(self.dpkg.message, type(Message()))


class DpkgVersionsTest(unittest.TestCase):

    def test_get_epoch(self):
        self.assertEqual(Dpkg.get_epoch('0'), (0, '0'))
        self.assertEqual(Dpkg.get_epoch('0:0'), (0, '0'))
        self.assertEqual(Dpkg.get_epoch('1:0'), (1, '0'))
        self.assertRaises(DpkgVersionError, Dpkg.get_epoch, '1a:0')

    def test_get_upstream(self):
        self.assertEqual(Dpkg.get_upstream('00'), ('00', '0'))
        self.assertEqual(Dpkg.get_upstream('foo'), ('foo', '0'))
        self.assertEqual(Dpkg.get_upstream('foo-bar'), ('foo', 'bar'))
        self.assertEqual(Dpkg.get_upstream('foo-bar-baz'), ('foo-bar', 'baz'))

    def test_split_full_version(self):
        self.assertEqual(Dpkg.split_full_version('00'), (0, '00', '0'))
        self.assertEqual(Dpkg.split_full_version('00-00'), (0, '00', '00'))
        self.assertEqual(Dpkg.split_full_version('0:0'), (0, '0', '0'))
        self.assertEqual(Dpkg.split_full_version('0:0-0'), (0, '0', '0'))
        self.assertEqual(Dpkg.split_full_version('0:0.0'), (0, '0.0', '0'))
        self.assertEqual(Dpkg.split_full_version('0:0.0-0'), (0, '0.0', '0'))
        self.assertEqual(Dpkg.split_full_version('0:0.0-00'), (0, '0.0', '00'))

    def test_get_alpha(self):
        self.assertEqual(Dpkg.get_alphas(''), ('', ''))
        self.assertEqual(Dpkg.get_alphas('0'), ('', '0'))
        self.assertEqual(Dpkg.get_alphas('00'), ('', '00'))
        self.assertEqual(Dpkg.get_alphas('0a'), ('', '0a'))
        self.assertEqual(Dpkg.get_alphas('a'), ('a', ''))
        self.assertEqual(Dpkg.get_alphas('a0'), ('a', '0'))

    def test_get_digits(self):
        self.assertEqual(Dpkg.get_digits('00'), (0, ''))
        self.assertEqual(Dpkg.get_digits('0'), (0, ''))
        self.assertEqual(Dpkg.get_digits('0a'), (0, 'a'))
        self.assertEqual(Dpkg.get_digits('a'), (0, 'a'))
        self.assertEqual(Dpkg.get_digits('a0'), (0, 'a0'))

    def test_listify(self):
        self.assertEqual(Dpkg.listify('0'), ['', 0])
        self.assertEqual(Dpkg.listify('00'), ['', 0])
        self.assertEqual(Dpkg.listify('0a'), ['', 0, 'a', 0])
        self.assertEqual(Dpkg.listify('a0'), ['a', 0])
        self.assertEqual(Dpkg.listify('a00'), ['a', 0])
        self.assertEqual(Dpkg.listify('a'), ['a', 0])

    def test_dstringcmp(self):
        self.assertEqual(Dpkg.dstringcmp('~', '.'), -1)
        self.assertEqual(Dpkg.dstringcmp('~', 'a'), -1)
        self.assertEqual(Dpkg.dstringcmp('a', '.'), -1)
        self.assertEqual(Dpkg.dstringcmp('a', '~'), 1)
        self.assertEqual(Dpkg.dstringcmp('.', '~'), 1)
        self.assertEqual(Dpkg.dstringcmp('.', 'a'), 1)
        self.assertEqual(Dpkg.dstringcmp('.', '.'), 0)
        self.assertEqual(Dpkg.dstringcmp('0', '0'), 0)
        self.assertEqual(Dpkg.dstringcmp('a', 'a'), 0)

        # taken from
        # http://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-Version
        self.assertEqual(
            sorted(['a', '', '~', '~~a', '~~'],
                   key=Dpkg.dstringcmp_key),
            ['~~', '~~a', '~', '', 'a'])

    def test_compare_revision_strings(self):
        # note that these are testing a single revision string, not the full
        # upstream+debian version.  IOW, "0.0.9-foo" is an upstream or debian
        # revision onto itself, not an upstream of 0.0.9 and a debian of foo.

        # equals
        self.assertEqual(Dpkg.compare_revision_strings('0', '0'), 0)
        self.assertEqual(Dpkg.compare_revision_strings('0', '00'), 0)
        self.assertEqual(Dpkg.compare_revision_strings('00.0.9', '0.0.9'), 0)
        self.assertEqual(Dpkg.compare_revision_strings('0.00.9-foo', '0.0.9-foo'), 0)
        self.assertEqual(Dpkg.compare_revision_strings('0.0.9-1.00foo', '0.0.9-1.0foo'), 0)

        # less than
        self.assertEqual(Dpkg.compare_revision_strings('0.0.9', '0.0.10'), -1)
        self.assertEqual(Dpkg.compare_revision_strings('0.0.9-foo', '0.0.10-foo'), -1)
        self.assertEqual(Dpkg.compare_revision_strings('0.0.9-foo', '0.0.10-goo'), -1)
        self.assertEqual(Dpkg.compare_revision_strings('0.0.9-foo', '0.0.9-goo'), -1)
        self.assertEqual(Dpkg.compare_revision_strings('0.0.10-foo', '0.0.10-goo'), -1)
        self.assertEqual(Dpkg.compare_revision_strings('0.0.9-1.0foo', '0.0.9-1.1foo'), -1)

        # greater than
        self.assertEqual(Dpkg.compare_revision_strings('0.0.10', '0.0.9'), 1)
        self.assertEqual(Dpkg.compare_revision_strings('0.0.10-foo', '0.0.9-foo'), 1)
        self.assertEqual(Dpkg.compare_revision_strings('0.0.10-foo', '0.0.9-goo'), 1)
        self.assertEqual(Dpkg.compare_revision_strings('0.0.9-1.0foo', '0.0.9-1.0bar'), 1)

    def test_compare_versions(self):
        # "This [the epoch] is a single (generally small) unsigned integer.
        # It may be omitted, in which case zero is assumed."
        self.assertEqual(Dpkg.compare_versions('0.0.0', '0:0.0.0'), 0)
        self.assertEqual(Dpkg.compare_versions('0:0.0.0-foo', '0.0.0-foo'), 0)
        self.assertEqual(Dpkg.compare_versions('0.0.0-a', '0:0.0.0-a'), 0)

        # "The absence of a debian_revision is equivalent to a debian_revision
        # of 0."
        self.assertEqual(Dpkg.compare_versions('0.0.0', '0.0.0-0'), 0)
        # tricksy:
        self.assertEqual(Dpkg.compare_versions('0.0.0', '0.0.0-00'), 0)

        # combining the above
        self.assertEqual(Dpkg.compare_versions('0.0.0-0', '0:0.0.0'), 0)

        # explicitly equal
        self.assertEqual(Dpkg.compare_versions('0.0.0', '0.0.0'), 0)
        self.assertEqual(Dpkg.compare_versions('1:0.0.0', '1:0.0.0'), 0)
        self.assertEqual(Dpkg.compare_versions('0.0.0-10', '0.0.0-10'), 0)
        self.assertEqual(Dpkg.compare_versions('2:0.0.0-1', '2:0.0.0-1'), 0)
        self.assertEqual(Dpkg.compare_versions('0:a.0.0-foo', '0:a.0.0-foo'), 0)

        # less than
        self.assertEqual(Dpkg.compare_versions('0.0.0-0', '0:0.0.1'), -1)
        self.assertEqual(Dpkg.compare_versions('0.0.0-0', '0:0.0.0-a'), -1)
        self.assertEqual(Dpkg.compare_versions('0.0.0-0', '0:0.0.0-1'), -1)
        self.assertEqual(Dpkg.compare_versions('0.0.9', '0.0.10'), -1)
        self.assertEqual(Dpkg.compare_versions('0.9.0', '0.10.0'), -1)
        self.assertEqual(Dpkg.compare_versions('9.0.0', '10.0.0'), -1)

        # greater than
        self.assertEqual(Dpkg.compare_versions('0.0.1-0', '0:0.0.0'), 1)
        self.assertEqual(Dpkg.compare_versions('0.0.0-a', '0:0.0.0-1'), 1)
        self.assertEqual(Dpkg.compare_versions('0.0.0-a', '0:0.0.0-0'), 1)
        self.assertEqual(Dpkg.compare_versions('0.0.9', '0.0.1'), 1)
        self.assertEqual(Dpkg.compare_versions('0.9.0', '0.1.0'), 1)
        self.assertEqual(Dpkg.compare_versions('9.0.0', '1.0.0'), 1)

        # unicode me harder
        self.assertEqual(Dpkg.compare_versions(u'2:0.0.44-1', u'2:0.0.44-nobin'), -1)
        self.assertEqual(Dpkg.compare_versions(u'2:0.0.44-nobin', u'2:0.0.44-1'), 1)
        self.assertEqual(Dpkg.compare_versions(u'2:0.0.44-1', u'2:0.0.44-1'), 0)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(DpkgTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
