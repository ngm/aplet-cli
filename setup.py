from setuptools import find_packages, setup

setup(
    name='aplet',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
        'gherkin3',
        'pyyaml',
        'graphviz'
    ],
    entry_points='''
        [console_scripts]
        aplet=aplet.main:cli
    ''',
)
