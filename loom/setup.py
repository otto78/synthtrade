#!/usr/bin/env python3
"""
LOOM — Setup Configuration
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="loom",
    version="1.0.12",
    author="Andrea Mazzarotto",
    author_email="andrea.mazzarotto@gmail.com",
    description="Weave intelligent agents into your development workflow",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/otto78/loom-framework",
    project_urls={
        "Documentation": "https://otto78.github.io/loom-framework/docs.html",
        "Source": "https://github.com/otto78/loom-framework",
        "Issues": "https://github.com/otto78/loom-framework/issues",
    },
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "loom": [
            "templates/**/*",
            "ide-configs/**/*",
            "directives/**/*",
            "execution/**/*",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        # No external dependencies for core framework
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "flake8>=6.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "loom-setup=loom.scripts.setup:main",
            "loom-task=loom.scripts.task:main",
            "loom-tdd=loom.scripts.task_tdd:main",
        ],
    },
    keywords="ai agents framework development workflow automation tdd",
    zip_safe=False,
)

