#!/usr/bin/env python3

from distutils.core import setup

setup(name         = 'httpgui',
      version      = '0.1',
      description  = 'Hot Penguin - Python GUI over HTTP without Javascript',
      author       = 'Antti Kervinen',
      author_email = 'antti.kervinen@gmail.com',
      py_modules   = ['httpgui'],
      classifiers  = [
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)',
          'Operating System :: POSIX :: Linux',
          'Operating System :: Microsoft :: Windows',
          'Programming Language :: Python :: 3 :: Only',
          ]
)
