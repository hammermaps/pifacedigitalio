from pathlib import Path
from setuptools import find_packages, setup


PIFACECOMMON_MIN_VERSION = '4.0.0'
VERSION_FILE = "pifacedigitalio/version.py"


def get_version():
    version_vars = {}
    with open(VERSION_FILE, encoding="utf-8") as f:
        code = compile(f.read(), VERSION_FILE, 'exec')
        exec(code, None, version_vars)
    return version_vars['__version__']


setup(
    name='pifacedigitalio',
    version=get_version(),
    description='The PiFace Digital I/O module.',
    author='Thomas Preston',
    author_email='thomas.preston@openlx.org.uk',
    url='http://piface.github.io/pifacedigitalio/',
    packages=find_packages(include=['pifacedigitalio', 'piface_mqtt']),
    long_description=(
        Path('README.md').read_text(encoding='utf-8')
        + Path('CHANGELOG').read_text(encoding='utf-8')
    ),
    classifiers=[
        "License :: OSI Approved :: GNU Affero General Public License v3 or "
        "later (AGPLv3+)",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords='piface digital raspberrypi openlx',
    license='GPLv3+',
    python_requires='>=3.8',
    install_requires=[
        'pifacecommon (=='+PIFACECOMMON_MIN_VERSION+')',
        'paho-mqtt>=1.6.1',
        'PyYAML>=6.0',
    ],
    scripts=['piface-mqtt.py'],
    data_files=[('share/pifacedigitalio', ['config.example.yaml', 'piface-mqtt.service'])],
)
