from setuptools import setup, find_namespace_packages

with open('README.md', 'r') as readme:
    long_description = readme.read()

exec(open('nwmaas/access/_version.py').read())

setup(
    name='nwmaas-access',
    version=__version__,
    description='Library package with service-side classes for handling client-side access details',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=['websockets', 'nwmaas-communication>=0.2.0'],
    packages=find_namespace_packages(exclude=('tests', 'schemas', 'ssl', 'src'))
)