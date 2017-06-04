#!/usr/bin/env python

from __future__ import print_function

import glob
import logging
import os
import sys

from pydpkg import Dpkg

logging.basicConfig()
log = logging.getLogger('dpkg_extract')
log.setLevel(logging.INFO)

PRETTY = """Filename: {0}
Size:     {1}
MD5:      {2}
SHA1:     {3}
SHA256:   {4}
Headers:
{5}"""


def indent(input_str, prefix):
    return '\n'.join(
        ['%s%s' % (prefix, x) for x in input_str.split('\n')]
    )

try:
    filenames = sys.argv[1:]
except KeyError:
    log.fatal('You must list at least one deb file as an argument')
    sys.exit(1)

for files in filenames:
    for fn in glob.glob(files):
        if not os.path.isfile(fn):
            log.warning('%s is not a file, skipping', fn)
        log.debug('checking %s', fn)
        dp = Dpkg(fn)
        print(PRETTY.format(
            fn, dp.filesize, dp.md5, dp.sha1, dp.sha256,
            indent(str(dp), '  ')
        ))
