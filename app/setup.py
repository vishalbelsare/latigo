import os
from setuptools import setup, find_packages

def read(fname):
    fn=os.path.join(os.path.dirname(os.path.abspath(__file__)), fname)
    print(f"Using README content from {fn}")
    with open(fn) as f:
        return f.read()
    return ""

setup(
    name = "gordo-client-ioc",
    version = "0.0.1",
    author = "Lennart Rolland",
    author_email = "lroll@equinor.com",
    description = ("A client to gordo machine learning system used by IOC to maintain models in production"),
    license = "AGPL-3.0",
    keywords = "gordo ioc client",
    url = "https://github.com/equinor/gordo-client-ioc",
    packages=find_packages(),
    zip_safe=True,
    long_description=read('README'),
    # From https://pypi.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Other Audience",
        "Topic :: Utilities",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.7",
        "Topic :: Other/Nonlisted Topic",
    ],
)
