from setuptools import setup, find_namespace_packages

with open('README.md', 'r') as readme:
    long_description = readme.read()

exec(open('dmod/evaluationservice/_version.py').read())

setup(
    name='dmod-evaluationservice',
    version=__version__,
    description='',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=['redis', 'dmod-evaluations'],
    packages=find_namespace_packages(exclude=('tests', 'test', 'deprecated', 'conf', 'schemas', 'ssl', 'src'))
)
