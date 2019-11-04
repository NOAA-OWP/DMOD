from setuptools import setup, find_packages

with open('README.md', 'r') as readme:
    long_description = readme.read()

exec(open('request_handler/_version.py').read())

setup(
    name='nwm_service_request_handler',
    version=__version__,
    description='',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    packages=find_packages(exclude=('tests', 'schemas', 'ssl', 'src'))
)