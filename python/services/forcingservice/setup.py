from setuptools import setup, find_namespace_packages

with open('README.md', 'r') as readme:
    long_description = readme.read()

exec(open('dmod/forcingservice/_version.py').read())

setup(
    name='dmod-forcingservice',
    version=__version__,
    description='',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=['numpy>=1.20.1'],
    packages=find_namespace_packages(exclude=('tests', 'schemas', 'ssl', 'src'))
)