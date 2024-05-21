from setuptools import setup, find_namespace_packages
from pathlib import Path

ROOT = Path(__file__).resolve().parent

with open(ROOT / 'README.md', 'r') as readme:
    long_description = readme.read()

exec(open(ROOT / 'dmod/partitionerservice/_version.py').read())

setup(
    name='dmod-partitionerservice',
    version=__version__,
    description='',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=['dmod-core>=0.1.0', 'dmod-communication>=0.7.1', 'dmod-modeldata>=0.7.1', 'dmod-scheduler>=0.12.1',
                      'dmod-externalrequests>=0.3.0'],
    packages=find_namespace_packages(exclude=['dmod.test', 'schemas', 'ssl', 'src'])
)
