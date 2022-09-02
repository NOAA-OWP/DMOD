from setuptools import setup, find_namespace_packages

with open('README.md', 'r') as readme:
    long_description = readme.read()

exec(open('dmod/schedulerservice/_version.py').read())

setup(
    name='dmod-schedulerservice',
    version=__version__,
    description='',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=['dmod-core>=0.2.0', 'dmod-communication>=0.8.0', 'dmod-scheduler>=0.9.0'],
    packages=find_namespace_packages(exclude=('tests', 'test', 'deprecated', 'conf', 'schemas', 'ssl', 'src'))
)
