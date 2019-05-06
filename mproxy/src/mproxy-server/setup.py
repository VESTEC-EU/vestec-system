from setuptools import setup

setup(
    # fmt: off
    name="mproxy-server",
    version="0.1.0",
    author="Rupert Nash",
    author_email="r.nash@epcc.ed.ac.uk",
    description="Machine Proxy server",
    packages=[
        "mproxy.server"
        ],
    install_requires=[
        "mproxy-core",
        "pika",
        "fabric"
        ]
)
