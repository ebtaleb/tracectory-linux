import sys
sys.path.append(".")
sys.path.append("./src")
import os
from data_sources import *
from threading import Lock
import leveldb
from time import time as systemtime
from analysis_funcs import *
#saveName = "t206"
import multiprocessing

try:
	import simplejson as json
except ImportError:
	import json

def usage():
	print >>sys.stderr, "storetodb.py <trace file> <memorys snapshot> <savename>"

def init():
	global t, in_str
	global traceFile, dumpFile
	#t = Trace("binaries/ex3/trace.txt")
	t = Trace(traceFile, False)
	#memorySpace = FossileStream("binaries/ex3/dump")
	memorySpace = FossileStream(dumpFile)
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

def getChangeMatrix(eip, regs, memorySpaceStream):
	global affectCache, instrCache

	#Analyze instruction
	if instrCache.has_key(eip):
		affects = affectCache[eip]
		instr = instrCache[eip]
	else:
		instr = asmbloc.dis_i(x86_mn,memorySpaceStream, eip, symbol_pool)
		origAffects =  get_instr_expr(instr, 123, [])
		affects = []
		for a in origAffects:
			affects += processAffect(a)
		affectCache[eip] = affects
		instrCache[eip] = instr

	if newEngine:
		try:
			changeMatrix = convertToUnikey(affects, regs)
		except:
			changeMatrix = None
			if not suppressErrors:
				raise
	else:
		changeMatrix = calcUnikeyRelations(affects, regs)
	if changeMatrix is None:
		return None
	else:
		newMatrix = {}
		for key,value in changeMatrix.items():
			k = normalize(key)
			newMatrix[k] = list([normalize(x) for x in value])
			#if isinstance(k, int):
				#We store memory location accesses to a list
			#	addToList(db, "write_%s" % str(k), str(curTime))

	record = { 'PC' : eip,
		  'disassembly' : str(instr),
		  'regs' : regs,
		  'changes' : newMatrix }
	return record

def processLine(line):
	eipData = line[6:line.find(" ",6)]
	if eipData.startswith("-"): return None
	try:
		eip = int(eipData, 16)
	except ValueError:
		#print "Warning: Couldn't parse %s\n" % eipData
		return None
	regData = line[line.find("EAX="):].split(",")
	regs = {}
	for val in regData:
		reg, value = val.split("=")
		regs[reg.strip()] = int(value,16)
	return getChangeMatrix(eip, regs, memorySpace)


def subprocessInit(dumpFile, useNewEngine, doSuppressErrors):
	global memorySpace, in_str
	global affectCache, instrCache
	global newEngine, suppressErrors
	newEngine = useNewEngine
	suppressErrors = doSuppressErrors

	affectCache = {}
	instrCache = {}
	print >>sys.stderr, "(pid=%d) Loading memory dump" % (os.getpid())
	memorySpace = FossileStream(dumpFile)
	in_str = bin_stream_file(memorySpace)
import pprint
def delegator(traceFile, dumpFile, newEngine, suppressErrors, db):
	fp = open(traceFile)

	cpus = multiprocessing.cpu_count() - 1
	print >>sys.stderr, "Delegating to %d processors" % (cpus)
	p = multiprocessing.Pool(cpus, subprocessInit, [dumpFile, newEngine, suppressErrors])
	t = 0
	lastTime = -1
	lastVal = -1

	prevResult = None

	while True:

		if lastTime != -1:

			print >>sys.stderr, t, (1.0*(t-lastVal))/(systemtime()-lastTime), "per second"
		lastTime = systemtime()
		lastVal = t
		lines = fp.readlines(1024*1024)
		if len(lines) == 0: break
		
		#Perform the hard lifting in a multi-core fashion
		result = p.map_async(processLine, lines)
		if prevResult is not None:
			results = prevResult.get()
			#Write results in this thread (not 100% optimal)
			for curRecord in results:
				if curRecord is not None:
					db.Put("instr_%d" % t, json.dumps(curRecord))
					changes = curRecord['changes']
					for key in changes.keys():
						if isinstance(key, int):
							addToList(db, "write_%s" % str(key), str(t))
					
				t += 1		
		prevResult = result



	db.Put("maxTime", str(t - 1))
	

def process(traceFile, dumpFile):
	print >>sys.stderr, "Using old engine"
	db = leveldb.LevelDB("./db/%s_oldEngine" % saveName)
	delegator(traceFile, dumpFile, False, False,  db = db)
	print >>sys.stderr, "Using new engine"
	newDb = leveldb.LevelDB("./db/%s_newEngine" % saveName)
	delegator(traceFile, dumpFile, True,  True, newDb)


if __name__ == '__main__':
	if len(sys.argv) != 4:
		usage()
		sys.exit(1)
	saveName = sys.argv[3]
	traceFile = sys.argv[1]
	dumpFile = sys.argv[2]
	process(traceFile, dumpFile)
	
