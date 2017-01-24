
# stdlib imports
import os
import tarfile

from StringIO import StringIO
from rfc822 import Message
from gzip import GzipFile

# pypi imports
from arpy import Archive

REQUIRED_HEADERS = ('package', 'version', 'architecture')


class DpkgError(Exception):
    pass


class DpkgVersionError(Exception):
    pass


class DpkgMissingControlFile(DpkgError):
    pass


class DpkgMissingControlGzipFile(DpkgError):
    pass


class DpkgMissingRequiredHeaderError(DpkgError):
    pass


class Dpkg(object):

    """Class allowing import and manipulation of a debian package file."""

    def __init__(self, filename=None):
        self.headers = {}
        if not isinstance(filename, basestring):
            raise DpkgError('filename argument must be a string')
        if not os.path.isfile(filename):
            raise DpkgError('filename "%s" does not exist', filename)
        self.control_str, self._control_headers = self._process_dpkg_file(
            filename)
        for k in self._control_headers.keys():
            self.headers[k] = self._control_headers[k]

    def __repr__(self):
        return self.control_str

    def get_header(self, header):
        """ case-independent query for a control message header value """
        return self.headers.get(header.lower(), '')

    def compare_version_with(self, version_str):
        return Dpkg.compare_versions(
            self.get_header('version'),
            version_str)

    def _force_encoding(self, obj, encoding='utf-8'):
        if isinstance(obj, basestring):
            if not isinstance(obj, unicode):
                obj = unicode(obj, encoding)
        return obj

    def _process_dpkg_file(self, filename):
        dpkg = Archive(filename)
        dpkg.read_all_headers()

        if 'control.tar.gz' not in dpkg.archived_files:
            raise DpkgMissingControlGzipFile(
                'Corrupt dpkg file: no control.tar.gz file in ar archive.')

        control_tgz = dpkg.archived_files['control.tar.gz']

        # have to do an intermediate step because gzipfile doesn't support seek
        # from end; luckily control tars are tiny
        control_tar_intermediate = GzipFile(fileobj=control_tgz, mode='rb')
        tar_data = control_tar_intermediate.read()
        sio = StringIO(tar_data)
        control_tar = tarfile.open(fileobj=sio)

        # pathname in the tar could be ./control, or just control
        # (there would never be two control files...right?)
        tar_members = [os.path.basename(x.name)
                       for x in control_tar.getmembers()]
        if 'control' not in tar_members:
            raise DpkgMissingControlFile(
                'Corrupt dpkg file: no control file in control.tar.gz.')
        control_idx = tar_members.index('control')

        # at last!
        control_file = control_tar.extractfile(
            control_tar.getmembers()[control_idx])

        # beware: dpkg will happily let people drop random encodings into the
        # control file
        control_str = self._force_encoding(control_file.read())

        # now build the dict
        control_file.seek(0)
        control_headers = Message(control_file)

        for header in REQUIRED_HEADERS:
            if header not in control_headers:
                raise DpkgMissingRequiredHeaderError(
                    'Corrupt control section; header: "%s" not found' % header)

        for header in control_headers:
            control_headers[header] = self._force_encoding(
                control_headers[header])

        return control_str, control_headers

    @staticmethod
    def get_epoch(version_str):
        """ Parse the epoch out of a package version string.
        Return (epoch, version); epoch is zero if not found."""
        try:
            # there could be more than one colon,
            # but we only care about the first
            e_index = version_str.index(':')
        except ValueError:
            # no colons means no epoch; that's valid, man
            return 0, version_str

        try:
            epoch = int(version_str[0:e_index])
        except ValueError:
            raise DpkgVersionError(
                'Corrupt dpkg version %s: epochs can only be ints, and '
                'epochless versions cannot use the colon character.' %
                version_str)

        return epoch, version_str[e_index + 1:]

    @staticmethod
    def get_upstream(version_str):
        """Given a version string that could potentially contain both an upstream
        revision and a debian revision, return a tuple of both.  If there is no
        debian revision, return 0 as the second tuple element."""
        try:
            d_index = version_str.rindex('-')
        except ValueError:
            # no hyphens means no debian version, also valid.
            return version_str, '0'

        return version_str[0:d_index], version_str[d_index+1:]

    @staticmethod
    def split_full_version(version_str):
        epoch, full_ver = Dpkg.get_epoch(version_str)
        upstream_rev, debian_rev = Dpkg.get_upstream(full_ver)
        return epoch, upstream_rev, debian_rev

    @staticmethod
    def get_alphas(revision_str):
        """Return a tuple of the first non-digit characters of a revision (which
        may be empty) and the remaining characters."""

        # get the index of the first digit
        for i, char in enumerate(revision_str):
            if char.isdigit():
                if i == 0:
                    return '', revision_str
                else:
                    return revision_str[0:i], revision_str[i:]
        # string is entirely alphas
        return revision_str, ''

    @staticmethod
    def get_digits(revision_str):
        """Return a tuple of the first integer characters of a revision (which
        may be empty) and the remains."""

        if not revision_str:
            return 0, ''

        # get the index of the first non-digit
        for i, char in enumerate(revision_str):
            if not char.isdigit():
                if i == 0:
                    return 0, revision_str
                else:
                    return int(revision_str[0:i]), revision_str[i:]
        # string is entirely digits
        return int(revision_str), ''

    @staticmethod
    def listify(revision_str):
        """Split a revision string into a list of alternating between strings and
        numbers, padded on either end to always be "str, int, str, int..." and
        always be of even length.  This allows us to trivially implement the
        comparison algorithm described at
        http://debian.org/doc/debian-policy/ch-controlfields.html#s-f-Version
        """
        result = []
        while revision_str:
            r1, remains = Dpkg.get_alphas(revision_str)
            r2, remains = Dpkg.get_digits(remains)
            result.extend([r1, r2])
            revision_str = remains
        return result

    @staticmethod
    def dstringcmp(a, b):
        """debian package version string section lexical sort algorithm

        "The lexical comparison is a comparison of ASCII values modified so
        that all the letters sort earlier than all the non-letters and so that
        a tilde sorts before anything, even the end of a part."
        """

        if a == b:
            return 0
        try:
            for i, char in enumerate(a):
                if char == b[i]:
                    continue
                # "a tilde sorts before anything, even the end of a part"
                # (emptyness)
                if char == '~':
                    return -1
                if b[i] == '~':
                    return 1
                # "all the letters sort earlier than all the non-letters"
                if char.isalpha() and not b[i].isalpha():
                    return -1
                if not char.isalpha() and b[i].isalpha():
                    return 1
                # otherwise lexical sort
                if ord(char) > ord(b[i]):
                    return 1
                if ord(char) < ord(b[i]):
                    return -1
        except IndexError:
            # a is longer than b but otherwise equal, hence greater
            # ...except for goddamn tildes
            if char == '~':
                return -1
            else:
                return 1
        # if we get here, a is shorter than b but otherwise equal, hence lesser
        # ...except for goddamn tildes
        if b[len(a)] == '~':
            return 1
        else:
            return -1

    @staticmethod
    def compare_revision_strings(rev1, rev2):
        if rev1 == rev2:
            return 0

        # listify pads results so that we will always be comparing ints to ints
        # and strings to strings (at least until we fall off the end of a list)
        list1 = Dpkg.listify(rev1)
        list2 = Dpkg.listify(rev2)

        if list1 == list2:
            return 0

        try:
            for i, item in enumerate(list1):
                # just in case
                if type(item) != type(list2[i]):
                    raise DpkgVersionError(
                        'Cannot compare %s to %s, something has gone horribly '
                        'awry.' % (item, list2[i]))
                # if the items are equal, next
                if item == list2[i]:
                    continue
                # numeric comparison
                if type(item) == int:
                    if item > list2[i]:
                        return 1
                    if item < list2[i]:
                        return -1
                else:
                    # string comparison
                    return Dpkg.dstringcmp(item, list2[i])
        except IndexError:
            # rev1 is longer than rev2 but otherwise equal, hence greater
            return 1
        # rev1 is shorter than rev2 but otherwise equal, hence lesser
        return -1

    @staticmethod
    def compare_versions(ver1, ver2):
        if ver1 == ver2:
            return 0

        # note the string conversion: the debian policy here explicitly
        # specifies ASCII string comparisons, so if you are mad enough to
        # actually cram unicode characters into your package name, you are on
        # your own.
        epoch1, upstream1, debian1 = Dpkg.split_full_version(str(ver1))
        epoch2, upstream2, debian2 = Dpkg.split_full_version(str(ver2))

        # if epochs differ, immediately return the newer one
        if epoch1 < epoch2:
            return -1
        if epoch1 > epoch2:
            return 1

        # then, compare the upstream versions
        upstr_res = Dpkg.compare_revision_strings(upstream1, upstream2)
        if upstr_res != 0:
            return upstr_res

        debian_res = Dpkg.compare_revision_strings(debian1, debian2)
        if debian_res != 0:
            return debian_res

        # at this point, the versions are equal, but due to an interpolated
        # zero in either the epoch or the debian version
        return 0
