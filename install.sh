#!/bin/bash
# mongodb
sudo apt-get -y install libtool autoconf g++ git python-dev build-essential python pkg-config mongodb python-pymongo
sudo service mongodb stop
sudo echo "bind_ip = 127.0.0.1" >> /etc/mongodb.conf
sudo service mongodb start

# miasm
sudo apt-get -y install mercurial python-cherrypy3 python-numpy python-ply screen python-zmq libzmq-dev

git clone https://github.com/serpilliere/elfesteem.git elfesteem
cd elfesteem
python setup.py build
sudo python setup.py install
cd ..

sudo apt-get -y install python-simplejson

git clone https://github.com/cea-sec/miasm.git miasm
cd miasm
python setup.py build
sudo python setup.py install
cd ..

#tracectory
git clone https://bitbucket.org/oebeling/tracectory.git
