from setuptools import setup

setup(
    name='awsume-appsync-account-plugin',
    version='1.0.0',
    author='Ken Winner',
    author_email='kcswinner@gmail.com',
    entry_points={
        'awsume': [
            'appsync = appsync'
        ]
    },
    py_modules=['appsync'],
    install_requires=[
        'requests',
        'requests_aws_sign'
    ],
    python_requires='>=3.5'
)