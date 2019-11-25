from distutils.core import setup
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='Httypist',
    version='0.1',
    packages=['httypist',],
    license='MIT',
    install_requires=requirements,
    long_description=open('README.md').read(),
)
