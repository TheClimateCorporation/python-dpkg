from distutils.core import setup

setup(
    name='pydpkg',
    packages=['pydpkg'], # this must be the same as the name above
    version='1.0',
    description='A python library for parsing debian package control headers and comparing version strings',
    author='Nathan J. Mehl',
    author_email='n@climate.com',
    url='https://github.com/theclimatecorporation/python-dpkg',
    download_url='https://github.com/theclimatecorporation/python-dpkg/tarball/1.0',
    keywords=['apt', 'debian', 'dpkg', 'packaging'],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: System :: Archiving :: Packaging",
    ],
)
