import os
import sys

from setuptools import setup, find_packages


major, minor1, minor2, release, serial = sys.version_info

readfile_kwargs = {"encoding": "utf-8"} if major >= 3 else {}


def readfile(filename):
    with open(filename, **readfile_kwargs) as fp:
        contents = fp.read()
    return contents


def get_packages(path):
    out = [path]
    for x in find_packages(path):
        out.append('{}/{}'.format(path, x))
    
    return out

packages = get_packages('rxgrpc')
setup(name='reactive-grpc',
      version='0.0.1',
      description='Python reactive gRPC support',
      long_description=readfile('README.rst'),
      url='https://github.com/fcracker79/reactive-grpc',
      author='fcracker79',
      author_email='fcracker79@gmail.com',
      license='MIT',
      packages=packages,
      install_requires=readfile(os.path.join(os.path.dirname(__file__), "requirements.txt")),
      zip_safe=False,
      test_suite="pycomb.test",
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'Topic :: Software Development',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
      ],
      keywords='reactive reactive-programming grpc protobuf'
      )
