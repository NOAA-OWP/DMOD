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
    install_requires=['numpy>=1.20.1', 'pandas', 'geopandas', 'dmod-communication>=0.3.0',
                      'hypy@git+git://github.com/noaa-owp/hypy@master#egg=hypy&subdirectory=python',
                      'hydrotools-nwis_client@git+git://github.com/noaa-owp/hydrotools#egg=hydrotools-nwis_client&subdirectory=python/nwis_client'],
    packages=find_namespace_packages(exclude=('tests', 'schemas', 'ssl', 'src'))
)