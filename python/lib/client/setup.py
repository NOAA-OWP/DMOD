from setuptools import setup, find_namespace_packages
from pathlib import Path

ROOT = Path(__file__).resolve().parent

try:
    with open(ROOT / 'README.md', 'r') as readme:
        long_description = readme.read()
except:
    long_description = ''

exec(open(ROOT / 'dmod/client/_version.py').read())

setup(
    name='dmod-client',
    version=__version__,
    description='Client interface package for components of the DMOD architecture',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    include_package_data=True,
    #install_requires=['websockets', 'jsonschema'],vi
    install_requires=['dmod-core>=0.15.0', 'websockets>=8.1', 'pydantic>=1.10.8,~=1.10', 'dmod-communication>=0.17.0',
                      'dmod-externalrequests>=0.6.0'],
    packages=find_namespace_packages(include=['dmod.*'], exclude=['dmod.test'])
)
