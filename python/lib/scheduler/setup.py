from setuptools import setup, find_namespace_packages
from pathlib import Path

ROOT = Path(__file__).resolve().parent

try:
    with open(ROOT / 'README.md', 'r') as readme:
        long_description = readme.read()
except:
    long_description = ''

exec(open(ROOT / 'dmod/scheduler/_version.py').read())

setup(
    name='dmod-scheduler',
    version=__version__,
    description='',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=['docker', 'Faker', 'dmod-communication>=0.17.0', 'dmod-modeldata>=0.7.1', 'dmod-redis>=0.1.0',
                      'dmod-core>=0.15.0', 'cryptography', 'uri', 'pyyaml', 'pydantic>=1.10.8,~=1.10'],
    packages=find_namespace_packages(exclude=['dmod.test', 'src'])
)

