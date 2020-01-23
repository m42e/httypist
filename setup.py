import os
import setuptools
from distutils.core import setup

root = os.path.dirname(os.path.abspath(__file__))

setuptools.setup(
    name="Httypist",
    version="0.1",
    packages=["httypist",],
    license="MIT",
    install_requires=["flask", "pyyaml", "requests", "celery", "dulwich", ],
    long_description=open(os.path.join(root, "README.md")).read(),
)
