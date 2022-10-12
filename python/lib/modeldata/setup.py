from setuptools import setup, find_namespace_packages

with open('README.md', 'r') as readme:
    long_description = readme.read()

exec(open('dmod/modeldata/_version.py').read())

setup(
    name='dmod-modeldata',
    version=__version__,
    description='',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=['numpy>=1.20.1', 'pandas', 'geopandas', 'dmod-communication>=0.9.1', 'dmod-core>=0.3.0', 'minio',
                      'aiohttp<=3.7.4', 'hypy@git+https://github.com/NOAA-OWP/hypy@master#egg=hypy&subdirectory=python'],
    packages=find_namespace_packages(exclude=('tests', 'schemas', 'ssl', 'src'))
)
