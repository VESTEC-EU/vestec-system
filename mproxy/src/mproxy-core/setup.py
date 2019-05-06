from setuptools import setup

# fmt: off
setup(
    name="mproxy-core",
    version="0.1.0",
    author="Rupert Nash",
    author_email="r.nash@epcc.ed.ac.uk",
    description="Machine Proxy core: config, API, model objects",
    packages=[
        'mproxy.core',
        ],
    install_requires=[
        'pyyaml',
        ]
    )
