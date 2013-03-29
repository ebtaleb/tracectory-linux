import sys
sys.path.append(".")
sys.path.append("./src")
import os
import json
import leveldb

db = leveldb.LevelDB("db/t206_oldEngine")

#times = list(db.RangeIter("instr","instu",include_value = False))
#times.sort()

for t in xrange(10000,1000000):
	time = "instr_%d" % t
	try:
		record = db.Get(str(time))
	except KeyError:
		continue
	print "== TIME: %s ==" % time
	print json.dumps(json.loads(record), indent = 4)
