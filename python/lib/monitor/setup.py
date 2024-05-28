from setuptools import setup, find_namespace_packages
from pathlib import Path

ROOT = Path(__file__).resolve().parent

try:
    with open(ROOT / 'README.md', 'r') as readme:
        long_description = readme.read()
except:
    long_description = ''

exec(open(ROOT / 'dmod/monitor/_version.py').read())

setup(
    name='dmod-monitor',
    version=__version__,
    description='',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=['docker>=7.1.0', 'Faker', 'dmod-core>=0.1.0', 'dmod-communication>=0.4.2', 'dmod-redis>=0.1.0',
                      'dmod-scheduler>=0.12.2'],
    packages=find_namespace_packages(exclude=['dmod.test', 'src'])
)
