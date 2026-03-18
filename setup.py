"""Setup script for MonitorSnap."""

from setuptools import setup, find_packages
from pathlib import Path

readme = Path(__file__).parent / "README.md"
long_description = readme.read_text(encoding="utf-8") if readme.exists() else ""

setup(
    name="monitorsnap",
    version="2.0.0",
    author="GTRows",
    description="Save and restore Windows display configurations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/GTRows/MonitorSnap",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Desktop Environment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.10",
    install_requires=[],
    entry_points={
        "console_scripts": [
            "monitorsnap=display_presets.__main__:main",
        ],
    },
    include_package_data=True,
    package_data={
        "display_presets": ["assets/icons/*"],
    },
)
