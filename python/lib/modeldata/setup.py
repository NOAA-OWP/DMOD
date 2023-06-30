from setuptools import setup, find_namespace_packages
from pathlib import Path

ROOT = Path(__file__).resolve().parent

try:
    with open(ROOT / "README.md", "r") as readme:
        long_description = readme.read()
except:
    long_description = ""

exec(open(ROOT / "dmod/modeldata/_version.py").read())

setup(
    name="dmod-modeldata",
    version=__version__,
    description="",
    long_description=long_description,
    author="",
    author_email="",
    url="",
    license="",
    install_requires=[
        "numpy>=1.20.1",
        "pandas",
        "fiona",
        "geopandas",
        "dmod-communication>=0.4.2",
        "dmod-core>=0.3.0",
        "minio",
        "aiohttp<=3.7.4",
        "shapely>=2.0.0",
        "hypy@git+https://github.com/NOAA-OWP/hypy@master#egg=hypy&subdirectory=python",
        "gitpython",
        "pydantic>=1.10.8,~=1.10",
    ],
    packages=find_namespace_packages(exclude=["dmod.test", "schemas", "ssl", "src"]),
)
