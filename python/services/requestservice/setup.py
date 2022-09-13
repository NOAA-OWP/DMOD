from setuptools import setup, find_namespace_packages

with open('README.md', 'r') as readme:
    long_description = readme.read()

exec(open('dmod/requestservice/_version.py').read())

setup(
    name='dmod-requestservice',
    version=__version__,
    description='',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=['websockets', 'dmod-core>=0.2.0', 'dmod-communication>=0.8.0', 'dmod-access>=0.2.0',
                      'dmod-externalrequests>=0.3.0'],
    packages=find_namespace_packages(exclude=('tests', 'schemas', 'ssl', 'src'))
)
