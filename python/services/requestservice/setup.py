from setuptools import setup, find_namespace_packages
from pathlib import Path

ROOT = Path(__file__).resolve().parent

with open(ROOT / 'README.md', 'r') as readme:
    long_description = readme.read()

exec(open(ROOT / 'dmod/requestservice/_version.py').read())

setup(
    name='dmod-requestservice',
    version=__version__,
    description='',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=['websockets', 'dmod-core>=0.16.0', 'dmod-communication>=0.19.1', 'dmod-access>=0.2.0',
                      'dmod-externalrequests>=0.6.0'],
    packages=find_namespace_packages(exclude=['dmod.test', 'schemas', 'ssl', 'src'])
)
