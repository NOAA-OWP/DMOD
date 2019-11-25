from setuptools import setup, find_packages

try:
    with open('README.md', 'r') as readme:
        long_description = readme.read()
except:
    long_description = ''

exec(open('nwm_maas/requests/_version.py').read())

setup(
    name='nwm_maas_communication',
    version=__version__,
    description='',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    #install_requires=['websockets', 'jsonschema'],
    install_requires=['jsonschema'],
    packages=find_packages(exclude=('tests'))
)