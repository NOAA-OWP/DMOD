from setuptools import setup, find_namespace_packages

with open('README.md', 'r') as readme:
    long_description = readme.read()

exec(open('nwmaas/request_handler/_version.py').read())

setup(
    name='nwmaas-request-handler',
    version=__version__,
    description='',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=['websockets', 'nwmaas-communication>=0.1.3'],
    packages=find_namespace_packages(exclude=('tests', 'schemas', 'ssl', 'src'))
)