
""" pydpkg: tools for inspecting dpkg archive files in python
            without any dependency on libapt
"""

from __future__ import absolute_import

# stdlib imports
import hashlib
import io
import logging
import os
import tarfile

from collections import defaultdict
from gzip import GzipFile
from email import message_from_string, message_from_file
from functools import cmp_to_key

# pypi imports
import six
import pgpy
from arpy import Archive

REQUIRED_HEADERS = ('package', 'version', 'architecture')

logging.basicConfig()


class DpkgError(Exception):
    """Base error class for Dpkg errors"""


class DscError(Exception):
    """Base error class for Dsc errors"""


class DpkgVersionError(DpkgError):
    """Corrupt or unparseable version string"""


class DpkgMissingControlFile(DpkgError):
    """No control file found in control.tar.gz"""


class DpkgMissingControlGzipFile(DpkgError):
    """No control.tar.gz file found in dpkg file"""


class DpkgMissingRequiredHeaderError(DpkgError):
    """Corrupt package missing a required header"""


class DscMissingFileError(DscError):
    """We were not able to find some of the files listed in the dsc"""


class DscBadChecksumsError(DscError):
    """Some of the files in the dsc have incorrect checksums"""


class DscBadSignatureError(DscError):
    """A dsc file has an invalid openpgp signature(s)"""


# pylint: disable=too-many-instance-attributes,too-many-public-methods
class Dpkg():

    """Class allowing import and manipulation of a debian package file."""

    def __init__(self, filename=None, ignore_missing=False, logger=None):
        """ Constructor for Dpkg object

        :param filename: string
        :param ignore_missing: bool
        :param logger: logging.Logger
        """
        self.filename = os.path.expanduser(filename)
        self.ignore_missing = ignore_missing
        if not isinstance(self.filename, six.string_types):
            raise DpkgError('filename argument must be a string')
        if not os.path.isfile(self.filename):
            raise DpkgError('filename "%s" does not exist' % filename)
        self._log = logger or logging.getLogger(__name__)
        self._fileinfo = None
        self._control_str = None
        self._headers = None
        self._message = None
        self._upstream_version = None
        self._debian_revision = None
        self._epoch = None

    def __repr__(self):
        return repr(self.control_str)

    def __str__(self):
        return six.text_type(self.control_str)

    def __getattr__(self, attr):
        """Overload getattr to treat control message headers as object
        attributes (so long as they do not conflict with an existing
        attribute).

        :param attr: string
        :returns: string
        :raises: AttributeError
        """
        # beware: email.Message[nonexistent] returns None not KeyError
        if attr in self.message:
            return self.message[attr]
        raise AttributeError("'Dpkg' object has no attribute '%s'" % attr)

    def __getitem__(self, item):
        """Overload getitem to treat the control message plus our local
        properties as items.

        :param item: string
        :returns: string
        :raises: KeyError
        """
        try:
            return getattr(self, item)
        except AttributeError:
            try:
                return self.__getattr__(item)
            except AttributeError:
                raise KeyError(item)

    @property
    def message(self):
        """Return an email.Message object containing the package control
        structure.

        :returns: email.Message
        """
        if self._message is None:
            self._message = self._process_dpkg_file(self.filename)
        return self._message

    @property
    def control_str(self):
        """Return the control message as a string

        :returns: string
        """
        if self._control_str is None:
            self._control_str = self.message.as_string()
        return self._control_str

    @property
    def headers(self):
        """Return the control message headers as a dict

        :returns: dict
        """
        if self._headers is None:
            self._headers = dict(self.message.items())
        return self._headers

    @property
    def fileinfo(self):
        """Return a dictionary containing md5/sha1/sha256 checksums
        and the size in bytes of our target file.

        :returns: dict
        """
        if self._fileinfo is None:
            h_md5 = hashlib.md5()
            h_sha1 = hashlib.sha1()
            h_sha256 = hashlib.sha256()
            with open(self.filename, 'rb') as dpkg_file:
                for chunk in iter(lambda: dpkg_file.read(128), b''):
                    h_md5.update(chunk)
                    h_sha1.update(chunk)
                    h_sha256.update(chunk)
            self._fileinfo = {
                'md5':      h_md5.hexdigest(),
                'sha1':     h_sha1.hexdigest(),
                'sha256':   h_sha256.hexdigest(),
                'filesize': os.path.getsize(self.filename)
            }
        return self._fileinfo

    @property
    def md5(self):
        """Return the md5 hash of our target file

        :returns: string
        """
        return self.fileinfo['md5']

    @property
    def sha1(self):
        """Return the sha1 hash of our target file

        :returns: string
        """
        return self.fileinfo['sha1']

    @property
    def sha256(self):
        """Return the sha256 hash of our target file

        :returns: string
        """
        return self.fileinfo['sha256']

    @property
    def filesize(self):
        """Return the size of our target file

        :returns: string
        """
        return self.fileinfo['filesize']

    @property
    def epoch(self):
        """Return the epoch portion of the package version string

        :returns: int
        """
        if self._epoch is None:
            self._epoch = self.split_full_version(self.version)[0]
        return self._epoch

    @property
    def upstream_version(self):
        """Return the upstream portion of the package version string

        :returns: string
        """
        if self._upstream_version is None:
            self._upstream_version = self.split_full_version(self.version)[1]
        return self._upstream_version

    @property
    def debian_revision(self):
        """Return the debian revision portion of the package version string

        :returns: string
        """
        if self._debian_revision is None:
            self._debian_revision = self.split_full_version(self.version)[2]
        return self._debian_revision

    def get(self, item, default=None):
        """Return an object property, a message header, None or the caller-
        provided default.

        :param item: string
        :param default:
        :returns: string
        """
        try:
            return self.__getitem__(item)
        except KeyError:
            return default

    def get_header(self, header):
        """Return an individual control message header

        :returns: string or None
        """
        return self.message.get(header)

    def compare_version_with(self, version_str):
        """Compare my version to an arbitrary version"""
        return Dpkg.compare_versions(self.get_header('version'), version_str)

    @staticmethod
    def _force_encoding(obj, encoding='utf-8'):
        """Enforce uniform text encoding"""
        if isinstance(obj, six.string_types):
            if not isinstance(obj, six.text_type):
                obj = six.text_type(obj, encoding)
        return obj

    def _process_dpkg_file(self, filename):
        dpkg_archive = Archive(filename)
        dpkg_archive.read_all_headers()
        try:
            control_tgz = dpkg_archive.archived_files[b'control.tar.gz']
        except KeyError:
            raise DpkgMissingControlGzipFile(
                'Corrupt dpkg file: no control.tar.gz file in ar archive.')
        self._log.debug('found controlgz: %s', control_tgz)

        # have to pass through BytesIO because gzipfile doesn't support seek
        # from end; luckily control tars are tiny
        with GzipFile(fileobj=control_tgz) as gzf:
            self._log.debug('opened gzip file: %s', gzf)
            with tarfile.open(fileobj=io.BytesIO(gzf.read())) as control_tar:
                self._log.debug('opened tar file: %s', control_tar)
                # pathname in the tar could be ./control, or just control
                # (there would never be two control files...right?)
                tar_members = [
                    os.path.basename(x.name) for x in control_tar.getmembers()]
                self._log.debug('got tar members: %s', tar_members)
                if 'control' not in tar_members:
                    raise DpkgMissingControlFile(
                        'Corrupt dpkg file: no control file in control.tar.gz')
                control_idx = tar_members.index('control')
                self._log.debug('got control index: %s', control_idx)
                # at last!
                control_file = control_tar.extractfile(
                    control_tar.getmembers()[control_idx])
                self._log.debug('got control file: %s', control_file)
                message_body = control_file.read()
                # py27 lacks email.message_from_bytes, so...
                if isinstance(message_body, bytes):
                    message_body = message_body.decode('utf-8')
                message = message_from_string(message_body)
                self._log.debug('got control message: %s', message)

        for req in REQUIRED_HEADERS:
            if req not in list(map(str.lower, message.keys())):
                if self.ignore_missing:
                    self._log.debug(
                        'Header "%s" not found in control message', req)
                    continue
                raise DpkgMissingRequiredHeaderError(
                    'Corrupt control section; header: "%s" not found' % req)
        self._log.debug('all required headers found')

        for header in message.keys():
            self._log.debug('coercing header to utf8: %s', header)
            message.replace_header(
                header, self._force_encoding(message[header]))
        self._log.debug('all required headers coerced')

        return message

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
        """Split a full version string into epoch, upstream version and
        debian revision.
        :param: version_str
        :returns: tuple """
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
                return revision_str[0:i], revision_str[i:]
        # string is entirely alphas
        return revision_str, ''

    @staticmethod
    def get_digits(revision_str):
        """Return a tuple of the first integer characters of a revision (which
        may be empty) and the remains."""
        # If the string is empty, return (0,'')
        if not revision_str:
            return 0, ''
        # get the index of the first non-digit
        for i, char in enumerate(revision_str):
            if not char.isdigit():
                if i == 0:
                    return 0, revision_str
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
            rev_1, remains = Dpkg.get_alphas(revision_str)
            rev_2, remains = Dpkg.get_digits(remains)
            result.extend([rev_1, rev_2])
            revision_str = remains
        return result

    # pylint: disable=invalid-name,too-many-return-statements
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
            return 1
        # if we get here, a is shorter than b but otherwise equal, hence lesser
        # ...except for goddamn tildes
        if b[len(a)] == '~':
            return 1
        return -1

    @staticmethod
    def compare_revision_strings(rev1, rev2):
        """Compare two debian revision strings as described at
        https://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-Version
        """
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
                if not isinstance(item, list2[i].__class__):
                    raise DpkgVersionError(
                        'Cannot compare %s to %s, something has gone horribly '
                        'awry.' % (item, list2[i]))
                # if the items are equal, next
                if item == list2[i]:
                    continue
                # numeric comparison
                if isinstance(item, int):
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
        """Function to compare two Debian package version strings,
        suitable for passing to list.sort() and friends."""
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

    @staticmethod
    def compare_versions_key(x):
        """Uses functools.cmp_to_key to convert the compare_versions()
        function to a function suitable to passing to sorted() and friends
        as a key."""
        return cmp_to_key(Dpkg.compare_versions)(x)

    @staticmethod
    def dstringcmp_key(x):
        """Uses functools.cmp_to_key to convert the dstringcmp()
        function to a function suitable to passing to sorted() and friends
        as a key."""
        return cmp_to_key(Dpkg.dstringcmp)(x)


class Dsc():
    """Class allowing import and manipulation of a debian source
       description (dsc) file."""
    def __init__(self, filename=None, logger=None):
        self.filename = os.path.expanduser(filename)
        self._dirname = os.path.dirname(self.filename)
        self._log = logger or logging.getLogger(__name__)
        self._message = None
        self._source_files = None
        self._sizes = None
        self._message_str = None
        self._checksums = None
        self._corrected_checksums = None
        self._pgp_message = None

    def __repr__(self):
        return repr(self.message_str)

    def __str__(self):
        return six.text_type(self.message_str)

    def __getattr__(self, attr):
        """Overload getattr to treat message headers as object
        attributes (so long as they do not conflict with an existing
        attribute).

        :param attr: string
        :returns: string
        :raises: AttributeError
        """
        self._log.debug('grabbing attr: %s', attr)
        if attr in self.__dict__:
            return self.__dict__[attr]
        # handle attributes with dashes :-(
        munged = attr.replace('_', '-')
        # beware: email.Message[nonexistent] returns None not KeyError
        if munged in self.message:
            return self.message[munged]
        raise AttributeError("'Dsc' object has no attribute '%s'" % attr)

    def __getitem__(self, item):
        """Overload getitem to treat the message plus our local
        properties as items.

        :param item: string
        :returns: string
        :raises: KeyError
        """
        self._log.debug('grabbing item: %s', item)
        try:
            return getattr(self, item)
        except AttributeError:
            try:
                return self.__getattr__(item)
            except AttributeError:
                raise KeyError(item)

    def get(self, item, ret=None):
        """Public wrapper for getitem"""
        try:
            return self.__getitem__(item)
        except KeyError:
            return ret

    @property
    def message(self):
        """Return an email.Message object containing the parsed dsc file"""
        self._log.debug('accessing message property')
        if self._message is None:
            self._message = self._process_dsc_file()
        return self._message

    @property
    def headers(self):
        """Return a dictionary of the message items"""
        if self._message is None:
            self._message = self._process_dsc_file()
        return dict(self._message.items())

    @property
    def pgp_message(self):
        """Return a pgpy.PGPMessage object containing the signed dsc
        message (or None if the message is unsigned)"""
        if self._message is None:
            self._message = self._process_dsc_file()
        return self._pgp_message

    @property
    def source_files(self):
        """Return a list of source files found in the dsc file"""
        if self._source_files is None:
            self._source_files = self._process_source_files()
        return [x[0] for x in self._source_files]

    @property
    def all_files_present(self):
        """Return true if all files listed in the dsc have been found"""
        if self._source_files is None:
            self._source_files = self._process_source_files()
        return all([x[2] for x in self._source_files])

    @property
    def all_checksums_correct(self):
        """Return true if all checksums are correct"""
        return not self.corrected_checksums

    @property
    def corrected_checksums(self):
        """Returns a dict of the CORRECT checksums in any case
        where the ones provided by the dsc file are incorrect."""
        if self._corrected_checksums is None:
            self._corrected_checksums = self._validate_checksums()
        return self._corrected_checksums

    @property
    def missing_files(self):
        """Return a list of all files from the dsc that we failed to find"""
        if self._source_files is None:
            self._source_files = self._process_source_files()
        return [x[0] for x in self._source_files if x[2] is False]

    @property
    def sizes(self):
        """Return a list of source files found in the dsc file"""
        if self._source_files is None:
            self._source_files = self._process_source_files()
        return {(x[0], x[1]) for x in self._source_files}

    @property
    def message_str(self):
        """Return the dsc message as a string

        :returns: string
        """
        if self._message_str is None:
            self._message_str = self.message.as_string()
        return self._message_str

    @property
    def checksums(self):
        """Return a dictionary of checksums for the source files found
        in the dsc file, keyed first by hash type and then by filename."""
        if self._checksums is None:
            self._checksums = self._process_checksums()
        return self._checksums

    def validate(self):
        """Raise exceptions if files are missing or checksums are bad."""
        if not self.all_files_present:
            raise DscMissingFileError(
                [x[0] for x in self._source_files if not x[2]])
        if not self.all_checksums_correct:
            raise DscBadChecksumsError(self.corrected_checksums)

    def _process_checksums(self):
        """Walk through the dsc message looking for any keys in the
        format 'Checksum-hashtype'.  Return a nested dictionary in
        the form {hashtype: {filename: {digest}}}"""
        self._log.debug('process_checksums()')
        sums = {}
        for key in self.message.keys():
            if key.lower().startswith('checksums'):
                hashtype = key.split('-')[1].lower()
            # grrrrrr debian :( :( :(
            elif key.lower() == 'files':
                hashtype = 'md5'
            else:
                continue
            sums[hashtype] = {}
            source = self.message[key]
            for line in source.split('\n'):
                if line:  # grrr py3--
                    digest, _, filename = line.strip().split(' ')
                    pathname = os.path.abspath(
                        os.path.join(self._dirname, filename))
                    sums[hashtype][pathname] = digest
        return sums

    def _internalize_message(self, msg):
        """Ugh: the dsc message body may not include a Files or
        Checksums-foo entry for _itself_, which makes for hilarious
        misadventures up the chain.  So, pfeh, we add it."""
        self._log.debug('internalize_message()')
        base = os.path.basename(self.filename)
        size = os.path.getsize(self.filename)
        for key, source in msg.items():
            self._log.debug('processing key: %s', key)
            if key.lower().startswith('checksums'):
                hashtype = key.split('-')[1].lower()
            elif key.lower() == 'files':
                hashtype = 'md5'
            else:
                continue
            found = []
            for line in source.split('\n'):
                if line:  # grrr
                    found.append(line.strip().split(' '))
            files = [x[2] for x in found]
            if base not in files:
                self._log.debug('dsc file not found in %s: %s', key, base)
                self._log.debug('getting hasher for %s', hashtype)
                hasher = getattr(hashlib, hashtype)()
                self._log.debug('hashing file')
                with open(self.filename, 'rb') as fileobj:
                    # pylint: disable=cell-var-from-loop
                    for chunk in iter(lambda: fileobj.read(1024), b''):
                        hasher.update(chunk)
                    self._log.debug('completed hashing file')
                self._log.debug('got %s digest: %s',
                                hashtype, hasher.hexdigest())
                newline = '\n {0} {1} {2}'.format(
                    hasher.hexdigest(), size, base)
                self._log.debug('new line: %s', newline)
                msg.replace_header(key, msg[key] + newline)
        return msg

    def _process_dsc_file(self):
        """Extract the dsc message from a file: parse the dsc body
        and return an email.Message object.  Attempt to extract the
        RFC822 message from an OpenPGP message if necessary."""
        self._log.debug('process_dsc_file()')
        if not self.filename.endswith('.dsc'):
            self._log.debug(
                'File %s does not appear to be a dsc file; pressing '
                'on but we may experience some turbulence and possibly '
                'explode.', self.filename)
        try:
            self._pgp_message = pgpy.PGPMessage.from_file(self.filename)
            self._log.debug('Found pgp signed message')
            msg = message_from_string(self._pgp_message.message)
        except TypeError as ex:
            self._log.exception(ex)
            self._log.fatal(
                'dsc file %s has a corrupt signature: %s', self.filename, ex)
            raise DscBadSignatureError
        except IOError as ex:
            self._log.fatal('Could not read dsc file "%s": %s',
                            self.filename, ex)
            raise
        except (ValueError, pgpy.errors.PGPError) as ex:
            self._log.warning('dsc file %s is not signed: %s',
                              self.filename, ex)
            with open(self.filename) as fileobj:
                msg = message_from_file(fileobj)
        msg = self._internalize_message(msg)
        return msg

    def _process_source_files(self):
        """Walk through the list of lines in the 'Files' section of
        the dsc message, and verify that the file exists in the same
        location on our filesystem as the dsc file.  Return a list
        of tuples: the normalized pathname for the file, the
        size of the file (as claimed by the dsc) and whether the file
        is actually present in the filesystem locally.

        Also extract the file size from the message lines and fill
        out the _files dictionary.
        """
        self._log.debug('process_source_files()')
        filenames = []
        try:
            files = self.message['Files']
        except KeyError:
            self._log.fatal('DSC file "%s" does not have a Files section',
                            self.filename)
            raise
        for line in files.split('\n'):
            if line:
                _, size, filename = line.strip().split(' ')
                pathname = os.path.abspath(
                    os.path.join(self._dirname, filename))
                filenames.append(
                    (pathname, int(size), os.path.isfile(pathname)))
        return filenames

    def _validate_checksums(self):
        """Iterate over the dict of asserted checksums from the
        dsc file.  Check each in turn.  If any checksum is invalid,
        append the correct checksum to a similarly structured dict
        and return them all at the end."""
        self._log.debug('validate_checksums()')
        bad_hashes = defaultdict(lambda: defaultdict(None))
        for hashtype, filenames in six.iteritems(self.checksums):
            for filename, digest in six.iteritems(filenames):
                hasher = getattr(hashlib, hashtype)()
                with open(filename, 'rb') as fileobj:
                    # pylint: disable=cell-var-from-loop
                    for chunk in iter(lambda: fileobj.read(128), b''):
                        hasher.update(chunk)
                if hasher.hexdigest() != digest:
                    bad_hashes[hashtype][filename] = hasher.hexdigest()
        return dict(bad_hashes)
