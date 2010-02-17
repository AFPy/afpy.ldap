#!/bin/python

LDAP="2.4.21"
PYLDAP="2.3.10"
PYTHON="python2.5"

DIR="$PWD/openldap-$LDAP"
wget "ftp://ftp.openldap.org/pub/OpenLDAP/openldap-release/openldap-$LDAP.tgz"

tar xzf openldap-$LDAP.tgz
cd $DIR
./configure --enable-bdb=no --enable-hdb=no --prefix=$PWD && make && make install
cd ..

wget "http://pypi.python.org/packages/source/p/python-ldap/python-ldap-$PYLDAP.tar.gz"
tar xvf python-ldap-$PYLDAP.tar.gz
cd python-ldap-$PYLDAP
perl -pe "s/\/usr\/local\/openldap-2.3/$(echo $DIR | perl -pe "s/\//\\\\\//g")/" setup.cfg > setup.cfg.1
mv setup.cfg.1 setup.cfg
$PYTHON setup.py bdist_egg

