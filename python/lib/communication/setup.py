from setuptools import setup, find_namespace_packages

try:
    with open('README.md', 'r') as readme:
        long_description = readme.read()
except:
    long_description = ''

exec(open('dmod/communication/_version.py').read())

setup(
    name='dmod-communication',
    version=__version__,
    description='Communications library package for components of the National Water Model as a Service architecture',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    include_package_data=True,
    #install_requires=['websockets', 'jsonschema'],vi
    install_requires=['websockets>=8.1', 'jsonschema', 'redis'],
    packages=find_namespace_packages(include=['dmod.*'], exclude=('tests'))
)