import sys
from setuptools import setup

if not sys.version_info >= (3, 5):
    sys.exit('Sorry, only Python 3.5 or later is supported')

setup(
    name='crypto_market_quotes',
    version='0.0.1',
    description='Getting crypto market data',
    url='https://github.com/dperezrada/marketquotes',
    author='Felipe Aránguiz, Daniel Pérez',
    authoremail='faranguiz575@gmail.com, dperezrada@gmail.com',
    license='MIT',
    packages=[
        'crypto_market_quotes'
    ],
    package_dir={
        'crypto_market_quotes': 'crypto_market_quotes',
    },
    install_requires=[
        'requests',
    ],
    tests_require=[
        # 'python-decouple',
    ],
    zip_safe=True
)
