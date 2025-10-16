from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="govbizops",
    version="0.1.0",
    description="Python library for collecting government contract opportunities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/govbizops",
    packages=["govbizops"],
    package_dir={"govbizops": "."},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    install_requires=[
        "requests>=2.31.0",
        "python-dateutil>=2.8.2",
        "python-dotenv>=1.0.0",
        "flask>=3.0.0",
        "beautifulsoup4>=4.12.0",
        "openai>=1.0.0",
        "playwright>=1.40.0",
    ],
    python_requires=">=3.7",
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "govbizops=main:main",
            "govbizops-setup=setup_playwright:main",
        ],
    },
)