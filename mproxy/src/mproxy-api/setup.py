from setuptools import setup

setup(
    name="mproxy-api",
    version="0.1.0",
    author="Rupert Nash",
    author_email="r.nash@epcc.ed.ac.uk",
    description="Machine Proxy API between client and server",
    packages=[
        'mproxy',
        'mproxy.api',
        ],
    install_requires=[
        'pyyaml',
        ]
    )
