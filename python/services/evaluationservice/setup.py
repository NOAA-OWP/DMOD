from setuptools import setup, find_namespace_packages
from pathlib import Path

ROOT = Path(__file__).resolve().parent

with open(ROOT / 'README.md', 'r') as readme:
    long_description = readme.read()

exec(open(ROOT / 'dmod/evaluationservice/_version.py').read())

setup(
    name='dmod-evaluationservice',
    version=__version__,
    description='',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=[
        'redis',
        'dmod-evaluations',
        'channels',
        'channels-redis',
        'django-rq',
        'Django~=4.2',
        'djangorestframework',
        'geopandas'
    ],
    packages=find_namespace_packages(exclude=['dmod.test', 'deprecated', 'conf', 'schemas', 'ssl', 'src'])
)
