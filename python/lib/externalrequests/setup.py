from setuptools import setup, find_namespace_packages
from pathlib import Path

ROOT = Path(__file__).resolve().parent

try:
    with open(ROOT / 'README.md', 'r') as readme:
        long_description = readme.read()
except:
    long_description = ''

exec(open(ROOT / 'dmod/externalrequests/_version.py').read())

setup(
    name='dmod-externalrequests',
    version=__version__,
    description='Library package with classes for handling external interactions',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=['websockets', 'dmod-core>=0.1.0', 'dmod-communication>=1.0.0', 'dmod-access>=0.1.1'],
    packages=find_namespace_packages(exclude=['dmod.test', 'schemas', 'ssl', 'src'])
)
