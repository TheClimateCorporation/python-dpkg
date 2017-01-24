python-dpkg
===========

This library can be used to:

1. read and extract control data from Debian-format package files, even
   on platforms that generally lack a native implementation of dpkg

2. compare dpkg version strings, using a pure Python implementation of
   the algorithm described at
   https://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-Version

This is primarily intended for use on platforms that do not normally
ship [python-apt](http://apt.alioth.debian.org/python-apt-doc/) due to
licensing restrictions or the lack of a native libapt.so (e.g. macOS)

Currently only tested on Python 2.6 and 2.7.  Should run on any python2
distribution that can install the [arpy](https://pypi.python.org/pypi/arpy/)
library.
   

Usage
=====

Read and extract headers
------------------------

    >>> from pydpkg import Dpkg
    >>> dp = Dpkg('/tmp/testdeb_1:0.0.0-test_all.deb')

    >>> dp.headers
    {'maintainer': u'Climate Corp Engineering <no-reply@climate.com>', 'description': u'testdeb\n a bogus debian package for testing dpkg builds', 'package': u'testdeb', 'section': u'base', 'priority': u'extra', 'installed-size': u'0', 'version': u'1:0.0.0-test', 'architecture': u'all'}

    >>> print dp
    Package: testdeb
    Version: 1:0.0.0-test
    Section: base
    Priority: extra
    Architecture: all
    Installed-Size: 0
    Maintainer: Climate Corp Engineering <no-reply@climate.com>
    Description: testdeb
     a bogus debian package for testing dpkg builds

Get an arbitrary control header, case-independent
-------------------------------------------------

    >>> dp.get_header('version')
    u'1:0.0.0-test'

    >>> dp.get_header('VERSION')
    u'1:0.0.0-test'

Compare current version to a candidate version
----------------------------------------------

    >>> dp.compare_version_with('1.0')
    1

    >>> dp.compare_version_with('1:1.0')
    -1

Compare two arbitrary version strings
-------------------------------------

    >>> from pydpkg import Dpkg
    >>> ver_1 = '0:1.0-test1'
    >>> ver_2 = '0:1.0-test2'
    >>> Dpkg.compare_versions(ver_1, ver_2)
    -1

Use as a cmp function to sort a list of version strings
-------------------------------------------------------

    >>> from pydpkg import Dpkg
    >>> sorted(['0:1.0-test1', '1:0.0-test0', '0:1.0-test2'] , cmp=Dpkg.compare_versions)
    ['0:1.0-test1', '0:1.0-test2', '1:0.0-test0']
