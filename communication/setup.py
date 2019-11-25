from setuptools import setup, find_namespace_packages

try:
    with open('README.md', 'r') as readme:
        long_description = readme.read()
except:
    long_description = ''

exec(open('nwm_maas/communication/_version.py').read())

setup(
    name='nwm_maas_communication',
    version=__version__,
    description='',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    #install_requires=['websockets', 'jsonschema'],vi
    install_requires=['jsonschema'],
    packages=find_namespace_packages(include=['nwm_maas.*'], exclude=('tests'))
)