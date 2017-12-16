from distutils.core import setup
setup(
    name = 'accustom',
    version = '1.0.3',
    description = 'Custom resource library for AWS CloudFormation',
    long_description = 'Accustom is a library for responding to Custom Resources in AWS CloudFormation using the decorator pattern.',
    url = 'https://github.com/NightKhaos/accustom',
    author = 'Taylor Bertie',
    author_email = 'nightkhaos@gmail.com',
    license = 'MIT',
    download_url = 'https://github.com/NightKhaos/accustom/archive/1.0.3.tar.gz',
    keywords = ['cloudformation','lambda','custom','resource','decorator'],
    classifiers = [
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Application Frameworks',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
    packages = ['accustom', 'accustom.Exceptions'],
    install_requires=[
      'botocore>=1.5'
    ],
    python_requires='>=2.6, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, !=3.5.*, <4',
    )
