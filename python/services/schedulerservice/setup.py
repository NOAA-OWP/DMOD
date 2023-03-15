from setuptools import setup, find_namespace_packages
from pathlib import Path

ROOT = Path(__file__).resolve().parent

with open(ROOT / 'README.md', 'r') as readme:
    long_description = readme.read()

exec(open(ROOT / 'dmod/schedulerservice/_version.py').read())

setup(
    name='dmod-schedulerservice',
    version=__version__,
    description='',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=['dmod-core>=0.2.0', 'dmod-communication>=0.11.0', 'dmod-scheduler>=0.10.0'],
    packages=find_namespace_packages(exclude=['dmod.test', 'deprecated', 'conf', 'schemas', 'ssl', 'src'])
    )
