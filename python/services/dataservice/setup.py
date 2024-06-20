from setuptools import setup, find_namespace_packages
from pathlib import Path

ROOT = Path(__file__).resolve().parent

with open(ROOT / 'README.md', 'r') as readme:
    long_description = readme.read()

exec(open(ROOT / 'dmod/dataservice/_version.py').read())

setup(
    name='dmod-dataservice',
    version=__version__,
    description='',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=['dmod-core>=0.17.0', 'dmod-communication>=0.20.0', 'dmod-scheduler>=0.12.2',
                      'dmod-modeldata>=0.12.0', 'redis', "pydantic[dotenv]>=1.10.8,~=1.10", "fastapi", "uvicorn[standard]",
                      'ngen-config@git+https://github.com/noaa-owp/ngen-cal@master#egg=ngen-config&subdirectory=python/ngen_conf',
                      'ngen-cal@git+https://github.com/noaa-owp/ngen-cal@master#egg=ngen-config&subdirectory=python/ngen_cal'],
    packages=find_namespace_packages(exclude=['dmod.test', 'deprecated', 'conf', 'schemas', 'ssl', 'src'])
)
