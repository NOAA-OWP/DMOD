from setuptools import setup, find_namespace_packages
from pathlib import Path

ROOT = Path(__file__).resolve().parent

with open(ROOT / 'README.md', 'r') as readme:
    long_description = readme.read()

exec(open(ROOT / 'dmod/datarequestservice/_version.py').read())

setup(
    name='dmod-datarequestservice',
    version=__version__,
    description='',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=['flask', 'dmod-modeldata>=0.5.0'],
    packages=find_namespace_packages(exclude=['dmod.test', 'deprecated', 'conf', 'schemas', 'ssl', 'src'])
)
