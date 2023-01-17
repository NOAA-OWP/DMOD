from setuptools import setup, find_namespace_packages

try:
    with open('README.md', 'r') as readme:
        long_description = readme.read()
except:
    long_description = ''

exec(open('dmod/metrics/_version.py').read())

setup(
    name='dmod-metrics',
    version=__version__,
    description='Library package with classes and functions for performing post-processing metrics',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=[],
    packages=find_namespace_packages(exclude=['dmod.test', 'schemas', 'ssl', 'src'])
)
