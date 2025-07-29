from setuptools import setup, find_packages

setup(
    name='bheem-accounting',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[], # Add module-specific dependencies
    include_package_data=True,
    description='Bheem Accounting ERP module',
    author='Bheem Core Team',
    url='https://github.com/bheemverse/Bheem_Accounting'
)
