from setuptools import setup, find_namespace_packages

try:
    with open('README.md', 'r') as readme:
        long_description = readme.read()
except:
    long_description = ''

exec(open('dmod/access/_version.py').read())

setup(
    name='dmod-access',
    version=__version__,
    description='Library package with service-side classes for handling client-side access details',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=['websockets', 'dmod-communication>=0.1.1', 'dmod-redis>=0.1.0'],
    packages=find_namespace_packages(exclude=('tests', 'schemas', 'ssl', 'src'))
)