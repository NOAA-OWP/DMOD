from setuptools import setup, find_namespace_packages
from pathlib import Path

ROOT = Path(__file__).resolve().parent

try:
    with open(ROOT / 'README.md', 'r') as readme:
        long_description = readme.read()
except:
    long_description = ''

exec(open(ROOT / 'dmod/redis/_version.py').read())

setup(
    name='dmod-redis',
    version=__version__,
    description='Library package with utility classes and functions commonly used Redis operations',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=['redis'],
    packages=find_namespace_packages(exclude=('test'))
)
