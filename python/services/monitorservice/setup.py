from setuptools import setup, find_namespace_packages

with open('README.md', 'r') as readme:
    long_description = readme.read()

exec(open('nwmaas/monitorservice/_version.py').read())

setup(
    name='nwmaas-monitorservice',
    version=__version__,
    description='',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=[],
    packages=find_namespace_packages(exclude=('tests', 'schemas', 'ssl', 'src'))
)
