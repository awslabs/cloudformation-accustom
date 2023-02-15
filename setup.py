# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from setuptools import setup
import os


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='accustom',
    version='1.2.1',
    description='Accustom is a library for responding to Custom Resources in AWS CloudFormation using the decorator '
                'pattern.',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    url='https://github.com/awslabs/cloudformation-accustom',
    author='Taylor Bertie',
    author_email='bertiet@amazon.com',
    license='Apache-2.0',
    download_url='https://github.com/awslabs/cloudformation-accustom/archive/1.1.2.tar.gz',
    keywords=['cloudformation', 'lambda', 'custom', 'resource', 'decorator'],
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Application Frameworks',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: Apache Software License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
    ],
    packages=['accustom', 'accustom.Exceptions'],
    install_requires=[
        'botocore>=1.29',
        'boto3>=1.26',
        'requests>=2.25',
        'six>=1.16'
    ],
    python_requires='>=3, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, !=3.5.*, !=3.6.*, <4',
)
