import setuptools
from distutils.core import setup

__VERSION__ = '1.4.1'

setup(
    name='pydpkg',
    packages=['pydpkg'],  # this must be the same as the name above
    python_requires=">=3.4",
    version=__VERSION__,
    description='A python library for parsing debian package control headers and comparing version strings',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Nathan J. Mehl',
    author_email='n@climate.com',
    url='https://github.com/theclimatecorporation/python-dpkg',
    download_url='https://github.com/theclimatecorporation/python-dpkg/tarball/%s' % __VERSION__,
    keywords=['apt', 'debian', 'dpkg', 'packaging'],
    setup_requires=[
        'wheel'
    ],
    install_requires=[
        'arpy==1.1.1',
        'six==1.10.0',
        'PGPy==0.4.1'
    ],
    extras_require={
        'test': ['pep8==1.7.0', 'pytest==3.1.1', 'pylint==2.3.1'],
        'publish': ['twine']
    },
    scripts=[
        'scripts/dpkg-inspect.py'
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: System :: Archiving :: Packaging",
        ]
)
