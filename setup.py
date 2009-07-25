# -*- coding: utf-8 -*-
# Copyright (c) 2009 Gael Pasgrimaud
"""
This module contains the tool of gp.ldap
"""
import os
from setuptools import setup, find_packages

version = '0.1'

long_description = ''

setup(name='afpy.ldap',
      version=version,
      description="The afpy.ldap package",
      long_description=long_description,
      # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='ldap',
      author='Gael Pasgrimaud',
      author_email='gael@gawel.org',
      url='',
      license='MIT',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['afpy'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          # -*- Extra requirements: -*-
          'WebOb',
          'WebTest',
          'ConfigObject',
          'Formalchemy',
          'dataflake.ldapconnection',
          'repoze.what',
      ],
      entry_points="""
      # -*- Entry points: -*-
      [console_scripts]
      ldapgrep = gp.ldap.scripts:main

      [paste.app_factory]
      main = gp.ldap.wsgi:factory
      """,
      )

