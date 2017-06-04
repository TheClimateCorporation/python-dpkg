from distutils.core import setup
setup(
    name='pydpkg',
    packages=['pydpkg'],  # this must be the same as the name above
    version='1.1',
    description='A python library for parsing debian package control headers and comparing version strings',
    author='Nathan J. Mehl',
    author_email='n@climate.com',
    url='https://github.com/theclimatecorporation/python-dpkg',
    download_url='https://github.com/theclimatecorporation/python-dpkg/tarball/1.1',
    keywords=['apt', 'debian', 'dpkg', 'packaging'],
    install_requires=[
        'arpy==1.1.1',
        'six==1.10.0'
    ],
    extras_require={
        'test': ['pep8==1.7.0', 'pytest==3.1.1', 'pylint==1.7.1']
    },
    scripts=[
        'scripts/dpkg-inspect.py'
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: System :: Archiving :: Packaging",
        ]
)
