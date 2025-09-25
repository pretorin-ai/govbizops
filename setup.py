from setuptools import setup, find_packages

setup(
    name="govbizops",
    version="0.1.0",
    description="Python library for collecting government contract opportunities",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "python-dateutil>=2.8.2",
        "python-dotenv>=1.0.0",
    ],
    python_requires=">=3.7",
)