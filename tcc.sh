#!/bin/bash

git clone http://repo.or.cz/tinycc.git
cd tinycc/ and git checkout release_0_9_26
./configure --disable-static
make
sudo make install