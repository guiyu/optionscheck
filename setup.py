# setup.py
from setuptools import setup, find_packages

setup(
    name="option_system",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'pandas>=1.3.0',
        'numpy>=1.21.0',
        'requests>=2.26.0',
        'yahooquery>=2.2.6',
        'scipy>=1.7.0',
        'click>=8.0.0',
        'pyyaml>=5.4.1'
    ],
)