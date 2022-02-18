from setuptools import setup, find_namespace_packages

with open('README.md', 'r') as readme:
    long_description = readme.read()

exec(open('dmod/monitorservice/_version.py').read())

setup(
    name='dmod-monitorservice',
    version=__version__,
    description='',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=['dmod-communication>=0.4.2', 'dmod-monitor>=0.3.0'],
    packages=find_namespace_packages(exclude=('tests', 'schemas', 'ssl', 'src'))
)
