from setuptools import setup, find_namespace_packages
from pathlib import Path

ROOT = Path(__file__).resolve().parent

try:
    with open(ROOT / "README.md", "r") as readme:
        long_description = readme.read()
except:
    long_description = ""

exec(open(ROOT / "dmod/hydrofabric/_version.py").read())

setup(
    name="dmod-hydrofabric",
    version=__version__,
    description="",
    long_description=long_description,
    author="",
    author_email="",
    url="",
    license="",
    install_requires=[],
    packages=find_namespace_packages(exclude=["dmod.test"]),
)
