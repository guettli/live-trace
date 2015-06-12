import setuptools


class PyTest(setuptools.Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import subprocess
        import sys

        errno = subprocess.call([sys.executable, 'runtests.py'])
        raise SystemExit(errno)


setuptools.setup(
    name='live-trace',
    version='2015.3',
    license="http://www.apache.org/licenses/LICENSE-2.0",
    long_description=open('README.txt').read(),
    packages=setuptools.find_packages(),
    install_requires=[],

    cmdclass={'test': PyTest},

    entry_points={
        'console_scripts': [
            'live-trace=live_trace.main:main',
        ],
    }
)
