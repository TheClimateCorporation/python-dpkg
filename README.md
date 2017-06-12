[![Build Status](https://travis-ci.org/TheClimateCorporation/python-dpkg.svg?branch=master)](https://travis-ci.org/TheClimateCorporation/python-dpkg)

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

Currently only tested on CPython 2.7 and 3.5, but at least in theory should run
on any python distribution that can install the [arpy](https://pypi.python.org/pypi/arpy/)
library.
   
Installing
==========

Install the 'pydpkg' package from [PyPi](https://pypi.python.org) using
the [pip](https://packaging.python.org/installing/) tool:

    $ pip install pydpkg
    Collecting pydpkg
      Downloading pydpkg-1.1-py2-none-any.whl
      Installing collected packages: pydpkg
      Successfully installed pydpkg-1.1

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

Interact directly with the package control message
--------------------------------------------------

    >>> dp.message
    <email.message.Message instance at 0x10895c6c8>
    >>> dp.message.get_content_type()
    'text/plain'

Get package file fingerprints
-----------------------------

    >>> dp.fileinfo
    {'sha256': '547500652257bac6f6bc83f0667d0d66c8abd1382c776c4de84b89d0f550ab7f', 'sha1': 'a5d28ae2f23e726a797349d7dd5f21baf8aa02b4', 'filesize': 910, 'md5': '149e61536a9fe36374732ec95cf7945d'}
    >>> dp.md5
    '149e61536a9fe36374732ec95cf7945d'
    >>> dp.sha1
    'a5d28ae2f23e726a797349d7dd5f21baf8aa02b4'
    >>> dp.sha256
    '547500652257bac6f6bc83f0667d0d66c8abd1382c776c4de84b89d0f550ab7f'
    >>> dp.filesize
    910

Get the components of the package version
-----------------------------------------

    >>> d.epoch
    1
    >>> d.upstream_version
    u'0.0.0'
    >>> d.debian_revision
    u'test'

Get an arbitrary control header, case-independent
-------------------------------------------------

    >>> d.version
    u'1:0.0.0-test'
    
    >>> d.VERSION
    u'1:0.0.0-test'
    
    >>> d.description
    u'testdeb\n a bogus debian package for testing dpkg builds'
    
    >>> d.get('nosuchheader', 'default')
    'default'

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

Use the `dpkg-inspect.py` script to inspect packages
----------------------------------------------------

    $ dpkg-inspect.py ~/testdeb*deb
    Filename: /Home/n/testdeb_1:0.0.0-test_all.deb
    Size:     910
    MD5:      149e61536a9fe36374732ec95cf7945d
    SHA1:     a5d28ae2f23e726a797349d7dd5f21baf8aa02b4
    SHA256:   547500652257bac6f6bc83f0667d0d66c8abd1382c776c4de84b89d0f550ab7f
    Headers:
      Package: testdeb
      Version: 1:0.0.0-test
      Section: base
      Priority: extra
      Architecture: all
      Installed-Size: 0
      Maintainer: Nathan Mehl <n@climate.com>
      Description: testdeb
       a bogus debian package for testing dpkg builds

