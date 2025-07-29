from setuptools import setup, find_packages

setup(
    name='bheem-accounting',
    version='1.0.0',
    packages=find_packages(include=["accounting", "accounting.*"]),
    install_requires=[],
    include_package_data=True,
    description='Bheem Accounting ERP module',
    author='Bheem Core Team',
    url='https://github.com/bheemverse/Bheem_Accounting'
)
