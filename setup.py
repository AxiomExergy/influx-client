from setuptools import setup, find_packages


def readme():
    try:
        with open('README.md', 'r') as doc:
            return doc.read()
    except IOError:
        return """\
# influx-client

See [GitHub](https://github.com/AxiomExergy/influx-client) for documentation.
"""


# Used for installing test dependencies directly
tests_require = [
    'mock',
    'nose',
    'flake8',
    'coverage<4.1'
]

setup(
    name='influx-client',
    version='1.6.0',
    description="InfluxDB client",
    long_description=readme(),
    long_description_content_type="text/markdown",
    license="Apache License v2.0",
    platforms=['any'],
    author="Jacob Alheid",
    author_email="shakefu@gmail.com",
    packages=find_packages(exclude=['test', 'test_*', 'fixtures']),
    install_requires=[
        'pytool',
        'requests',
        'simplejson',
        ],
    test_suite='nose.collector',
    tests_require=tests_require,
    # For installing test dependencies directly
    extras_require={'test': tests_require},
    keywords=['influx-client', 'database', 'influx', 'influxdb', 'client'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries',
        'Topic :: Utilities',
        'Topic :: Database',
        ],
    url="https://github.com/AxiomExergy/influx-client/",
    project_urls={
        "Bug Tracker": "https://github.com/AxiomExergy/influx-client/issues",
        "Documentation": "https://github.com/AxiomExergy/influx-client/",
        "Source Code": "https://github.com/AxiomExergy/influx-client/",
    }
)
