#!/usr/bin/env python3

import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    readme = fh.read()

with open("umzz/version.py","r", encoding="utf-8") as latest:
    version = latest.read().split('"')[1]



setuptools.setup(
    name="umzz",
    version=version,
    author="Adrian of Doom",
    author_email="a@slow.golf",
    description="SCTE-35 Injection for Adaptive Bitrate HLS",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/futzu/umzz",
    install_requires=[
        "new_reader >= 0.1.7",
        "iframes >= 0.0.7",
        "x9k3 >= 0.2.19",
        "m3ufu >=0.0.83",
        "threefive >= 2.4.9",
    ],
    scripts=["bin/umzz","bin/umzz2"],
    packages=setuptools.find_packages(),
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
    python_requires=">=3.6",
)
