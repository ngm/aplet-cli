from setuptools import setup

setup(
    name='aplet',
    version='0.1',
    py_modules=['aplet'],
    install_requires=[
        'Click',
        'gherkin3',
        'pyyaml',
        'graphviz'
    ],
    entry_points='''
        [console_scripts]
        aplet=aplet:aplet
    ''',
)
