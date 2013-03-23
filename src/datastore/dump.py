import sys
sys.path.append(".")
sys.path.append("./src")
import os
from traceparser import *
import json
import leveldb

db = leveldb.LevelDB("db/memcrypt_oldEngine")

times = list(db.RangeIter(include_value = False))
times.sort()

for time in times:
	record = db.Get(str(time))
	print "== TIME: %s ==" % time
	print json.dumps(json.loads(record), indent = 4)
