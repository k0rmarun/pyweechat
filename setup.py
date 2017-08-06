from setuptools import setup

setup(
    name='pyweechat',
    version='0.3',
    description='Python library for communicating with an weechat irc relay',
    url='http://github.com/k0rmarun/pyweechat',
    author='Niels Bernlöhr',
    author_email='kormarun@gmail.com',
    license='MIT',
    packages=['pyweechat'],
    zip_safe=False,
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Communications :: Chat :: Internet Relay Chat',
        'Topic :: Utilities',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ]
)
