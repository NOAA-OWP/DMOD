from setuptools import setup, find_namespace_packages
from pathlib import Path

ROOT = Path(__file__).resolve().parent

try:
    with open(ROOT / 'README.md', 'r') as readme:
        long_description = readme.read()
except:
    long_description = ''

exec(open(ROOT / 'dmod/communication/_version.py').read())

setup(
    name='dmod-communication',
    version=__version__,
    description='Communications library package for components of the National Water Model as a Service architecture',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    include_package_data=True,
    install_requires=['dmod-core>=0.4.2', 'websockets>=8.1', 'jsonschema', 'redis', 'pydantic>=1.10.8,~=1.10',
                      'ngen-config@git+https://github.com/noaa-owp/ngen-cal@master#egg=ngen-config&subdirectory=python/ngen_conf'],
    packages=find_namespace_packages(include=['dmod.*'], exclude=['dmod.test'])
)
