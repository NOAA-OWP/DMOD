from setuptools import setup, find_namespace_packages

try:
    with open('README.md', 'r') as readme:
        long_description = readme.read()
except:
    long_description = ''

exec(open('dmod/evaluations/_version.py').read())

setup(
    name='dmod-evaluations',
    version=__version__,
    description='Library package with classes for handling model evaluations',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=[
        'dmod-metrics',
        'pandas',
        'xarray',
        'h5py',
        'jsonpath-ng',
        'pint',
        'pytz',
        'requests'
    ],
    include_package_data=True,
    packages=find_namespace_packages(exclude=('tests', 'schemas', 'ssl', 'src'))
)