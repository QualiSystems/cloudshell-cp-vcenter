import os

from setuptools import find_packages, setup

with open(os.path.join("version.txt")) as version_file:
    version_from_file = version_file.read().strip()

with open("requirements.txt") as f_required:
    required = f_required.read().splitlines()

with open("test_requirements.txt") as f_tests:
    required_for_tests = f_tests.read().splitlines()

setup(
    name="cloudshell-cp-vcenter",
    author="Quali",
    url="https://github.com/QualiSystems/cloudshell-cp-vcenter",
    description=(
        "This Shell enables setting up vCenter as a cloud provider in CloudShell. "
        "It supports connectivity, and adds new deployment types for apps which can be used in "
        "CloudShell sandboxes."
    ),
    author_email="info@quali.com",
    packages=find_packages(),
    install_requires=required,
    tests_require=required_for_tests,
    test_suite="nose.collector",
    version=version_from_file,
    include_package_data=True,
    keywords="sandbox cloud virtualization vcenter cmp cloudshell",
    package_data={"": ["*.txt"]},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 3.7",
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: Apache Software License",
    ],
)
