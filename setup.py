import setuptools
import pip.req

from setuptools.command.test import test as TestCommand
import sys

class PyTest(TestCommand):

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = ['--pyargs', 'live_trace']
        self.test_suite = True

    def run_tests(self):
        #import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


setuptools.setup(
    name='live-trace',
    version='2014.1',
    license="http://www.apache.org/licenses/LICENSE-2.0",
    long_description=open('README.txt').read(),
    packages=setuptools.find_packages(),
    install_requires=[],

    cmdclass = {'test': PyTest},

    entry_points={
        'console_scripts': [
            'live-trace=live_trace:main',
            ],
        }
    )
