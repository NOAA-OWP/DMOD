from setuptools import setup, find_namespace_packages
from pathlib import Path

ROOT = Path(__file__).resolve().parent

try:
    with open(ROOT / 'README.md', 'r') as readme:
        long_description = readme.read()
except:
    long_description = ''

exec(open(ROOT / 'dmod/evaluations/_version.py').read())

setup(
    name='dmod-evaluations',
    version=__version__,
    description='Library package with classes for handling model evaluations',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=[
        'dmod-metrics',
        'pandas~=2.0',
        'xarray',
        'h5py',
        'jsonpath-ng',
        'pint',
        'pytz',
        'requests'
    ],
    include_package_data=True,
    packages=find_namespace_packages(exclude=['dmod.test', 'schemas', 'ssl', 'src'])
)
