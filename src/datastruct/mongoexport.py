#!/usr/bin/python
from pymongo import Connection as MongoClient
import os, sys

if len(sys.argv)<3:
	print "mongoexpory.py dbname collectionname"
	print "e.g. mongoexport.py t206 reads"
	sys.exit(1)

client = MongoClient()
db = client[sys.argv[1]]

coll = db[sys.argv[2]]
print coll.count()
for entry in coll.find():
	print entry['addr'], entry['time']
