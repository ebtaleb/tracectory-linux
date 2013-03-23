import sys
sys.path.append(".")
sys.path.append("./src")
import os
from traceparser import *
import json
from threading import Lock
import leveldb
from time import time as systemtime
saveName = "t206"
def init():
	global t, in_str
	#t = Trace("binaries/ex3/trace.txt")
	t = Trace("../raw/trace.txt", False)
	#memorySpace = FossileStream("binaries/ex3/dump")
	memorySpace = FossileStream("../raw/t206.fossile")
	in_str = bin_stream_file(memorySpace)

def normalize(x):
	if "numpy" in str(x.__class__):
		return int(x)
	
	return x

def addToList(db, listName, value):
	count = 0
	try:
		count = int(db.Get("%s_ctr" % listName))
	except KeyError:
		pass

	db.Put("%s_%d" % (listName,count), value)
	db.Put("%s_ctr" % listName, str(count + 1))


def dumpToDb(iterator, db):
	#for details in changeMatrixIterator(t.iterate(), t, in_str):
	count = 0
	lastTime = -1
	for details in iterator:
		if count%100000 == 0:
			print >>sys.stderr, count
			if lastTime!= -1:
				delay = systemtime() - lastTime
				print "%d instr/sec" % (100000./delay)
			lastTime = systemtime()
		curTime, eip, instr, changeMatrix = details
		newMatrix = {}
		count += 1
		if changeMatrix is None: continue

		for key,value in changeMatrix.items():
			k = normalize(key)
			newMatrix[k] = list([normalize(x) for x in value])
			addToList(db, "write_%s" % str(k), str(curTime))

		record = { 'PC' : eip,
			  'disassembly' : str(instr),
			  'regs' : t.regs,
			  'changes' : newMatrix }
		res = json.dumps(record)
		db.Put("instr_%d" % curTime, res)
		#print json.dumps(record, indent = 4)
	db.Put("maxTime",str(curTime))

print >>sys.stderr, "Using old engine"
init()
db = leveldb.LevelDB("./db/%s_oldEngine" % saveName)
dumpToDb(changeMatrixIterator(t.iterate(), t, in_str, newEngine = False), db)
print >>sys.stderr, "Using new engine"
init()
newDb = leveldb.LevelDB("./db/%s_newEngine" % saveName)
dumpToDb(changeMatrixIterator(t.iterate(), t, in_str, newEngine = True, suppressErrors = True), newDb)
