import setuptools
import pip.req


setuptools.setup(
    name='live-trace',
    version='2014.0',
    license="http://www.apache.org/licenses/LICENSE-2.0",
    long_description=open('README.txt').read(),
    packages=setuptools.find_packages(),
    install_requires=[],

    entry_points={
        'console_scripts': [
            'live-trace=live_trace.main:main',
            ],
        }
    )
