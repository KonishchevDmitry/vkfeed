import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

import PyRSS2Gen

from distutils.core import setup

setup(name = "PyRSS2Gen",        
      version = ".".join(map(str, PyRSS2Gen.__version__)),
      url ='http://www.dalkescientific.com/Python/PyRSS2Gen.html',
      license = 'BSD',
      description = 'A Python library for generating RSS 2.0 feeds.', 
      long_description = read('README'),
      
      author = 'Dalke Scientific Software',
      author_email = 'dalke@dalkescientific.com',  
      maintainer_email = 'pradeep@btbytes.com',
 
      packages = find_packages('.'),
      package_dir = {'':'.'},
      
      install_requires = ['setuptools'],
      
      classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python :: 2.3',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
      ],
      py_modules = ['PyRSS2Gen', 'test', 'example']
      )
