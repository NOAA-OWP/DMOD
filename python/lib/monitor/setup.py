from setuptools import setup, find_namespace_packages

try:
    with open('README.md', 'r') as readme:
        long_description = readme.read()
except:
    long_description = ''

exec(open('dmod/monitor/_version.py').read())

setup(
    name='dmod-monitor',
    version=__version__,
    description='',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=['docker', 'Faker', 'dmod-communication>=0.2.2', 'dmod-redis>=0.1.0', 'dmod-scheduler>=0.1.4'],
    packages=find_namespace_packages(exclude=('test', 'src'))
)
