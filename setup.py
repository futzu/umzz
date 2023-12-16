#!/usr/bin/env python3

import setuptools
import umzz

with open("README.md", "r", encoding="utf-8") as fh:
    readme = fh.read()

setuptools.setup(
    name="umzz",
    version=umzz.version(),
    author="Adrian of Doom",
    author_email="a@slow.golf",
    description=" Ultra Mega Zoom Zoom is SCTE-35 Injection for Adaptive Bitrate HLS",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/futzu/umzz",
    install_requires=[
        "new_reader >= 0.1.7",
        "iframes >= 0.0.7",
        "x9k3 >= 0.2.31",
        "m3ufu >=0.0.83",
        "threefive >= 2.4.9",
    ],
    py_modules=["umzz"],
    scripts=["bin/umzz","bin/umzz2"],
    platforms="all",
    # packages=setuptools.find_packages(),
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
    python_requires=">=3.6",
)
