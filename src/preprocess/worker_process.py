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

def normalize(x):
        if "numpy" in str(x.__class__):
                return int(x)
        
        return x

def analyzeInstruction(eip, regs, memorySpaceStream):
	global affectCache, instrCache

	# Disassemble the instruction and get its expression object.
	# (We use cached values, if available)
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

	if changeMatrix is None: return None

	#Normalize the change matrix
	newMatrix = {}
	for key,value in changeMatrix.items():
		k = normalize(key)
		newMatrix[k] = list([normalize(x) for x in value])

	#Build a record of the instruction and return it
	record = { 'PC' : eip,
		  'disassembly' : str(instr),
		  'regs' : regs,
		  'changes' : newMatrix }
	return record

def processLine(line):
	#Parse the line
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
		
	#Parse the info to actual analyzer
	return analyzeInstruction(eip, regs, memorySpace)


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

import zmq
def main():
	context = zmq.Context.instance()
	receive = context.socket(zmq.PULL)
	receive.connect("tcp://127.0.0.1:5555")

	sendResult = context.socket(zmq.PUSH)
	sendResult.connect("tcp://127.0.0.1:5556")

	workerControl = context.socket(zmq.SUB)
	workerControl.connect("tcp://127.0.0.1:5559")
	workerControl.setsockopt(zmq.SUBSCRIBE, "")

	poller = zmq.Poller()
	poller.register(workerControl, zmq.POLLIN)
	poller.register(receive, zmq.POLLIN)
	while True:
		socks = dict(poller.poll())
		if socks.get(workerControl) == zmq.POLLIN:
			dump, newEngine, suppressErrors = workerControl.recv_json()

			print >>sys.stderr, "workerControl",dump
			subprocessInit(dump, newEngine, suppressErrors)

			
		
		if socks.get(receive) == zmq.POLLIN:
			curTime, curLine = receive.recv_json()
			if curTime == -1:
				sendResult.send_json((curTime, curLine))
			else:
				try:
					record = processLine(curLine)
					sendResult.send_json((curTime, record))
				except:
					print "ERROR",curTime

			

if __name__ == '__main__':
	if len(sys.argv)==3:
		subprocessInit(sys.argv[1], True, False)
		print processLine(sys.argv[2])
	else:
		main()
