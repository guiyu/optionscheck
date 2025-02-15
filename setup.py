# setup.py
from setuptools import setup, find_packages

setup(
    name="option_system",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "yfinance",
        "pandas",
        "numpy",
        "click"
    ],
)