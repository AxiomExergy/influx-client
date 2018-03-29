from setuptools import setup, find_packages


# Used for installing test dependencies directly
tests_require = [
    'mock',
    'nose',
    'flake8',
]

setup(
    name='influx-client',
    version='1.0.0',
    description="InfluxDB client",
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
