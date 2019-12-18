from setuptools import setup, find_namespace_packages

try:
    with open('README.md', 'r') as readme:
        long_description = readme.read()
except:
    long_description = ''

exec(open('nwmaas/communication/_version.py').read())

setup(
    name='nwmaas-communication',
    version=__version__,
    description='Communications library package for components of the National Water Model as a Service architecture',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    include_package_data=True,
    #install_requires=['websockets', 'jsonschema'],vi
    install_requires=['websockets', 'jsonschema', 'redis'],
    packages=find_namespace_packages(include=['nwmaas.*'], exclude=('tests'))
)