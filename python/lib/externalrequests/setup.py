from setuptools import setup, find_namespace_packages

try:
    with open('README.md', 'r') as readme:
        long_description = readme.read()
except:
    long_description = ''

exec(open('nwmaas/externalrequests/_version.py').read())

setup(
    name='nwmaas-externalrequests',
    version=__version__,
    description='Library package with classes for handling external interactions',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=['websockets', 'nwmaas-communication>=0.2.0', 'nwmaas-access>=0.1.0'],
    packages=find_namespace_packages(exclude=('tests', 'schemas', 'ssl', 'src'))
)