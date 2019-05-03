from setuptools import setup

setup(
    name="mproxy-client",
    version="0.1.0",
    author="Rupert Nash",
    author_email="r.nash@epcc.ed.ac.uk",
    description="Machine Proxy client",
    namespace_packages=['mproxy'],
    packages=[
        'mproxy',
        'mproxy.client'
        ],        
    install_requires=[
        'mproxy-api',
        'pika',
        ]
)
