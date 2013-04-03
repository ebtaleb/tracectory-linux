import sys
sys.path.append(".")
sys.path.append("./src")
import os
from data_sources import *
from threading import Lock
import leveldb
from time import time as systemtime
from analysis_funcs import *
import multiprocessing
import time

try:
	import simplejson as json
except ImportError:
	import json

def usage():
	print >>sys.stderr, "%s <trace file> <memorys snapshot> <savename>" % sys.argv[0]

import zmq
context = zmq.Context()
workerControl = context.socket(zmq.PUB)
workerControl.bind("tcp://127.0.0.1:5559")
time.sleep(2)


dbOpenSend = context.socket(zmq.REQ)
dbOpenSend.connect("tcp://127.0.0.1:5558")

sendSocket = context.socket(zmq.PUSH)
sendSocket.bind("tcp://127.0.0.1:5555")

readySignalRecv = context.socket(zmq.SUB)
readySignalRecv.connect("tcp://127.0.0.1:5557")
readySignalRecv.setsockopt(zmq.SUBSCRIBE, "") 


def delegator(traceFile, dumpFile, newEngine, suppressErrors, dbName):
	workerControl.send_json( (dumpFile, newEngine, suppressErrors))

	dbOpenSend.send_json( {'status' : 'ok', 'db' : dbName } )	
	reply =  dbOpenSend.recv()
	assert reply == "OK"
	print "All set, waiting..."
	time.sleep(2)

	fp = open(traceFile)
	t = 0
	for line in fp:
		sendSocket.send_json((t, line))
		t += 1

	sendSocket.send_json( (-1, { 'entriesSent' : t  }))
	#sendSocket.send_json("READY")

	print "SENT!"
	poller = zmq.Poller()
	poller.register(readySignalRecv, zmq.POLLIN)
	while True:
		socks = dict(poller.poll())
		if socks.get(readySignalRecv) == zmq.POLLIN:
			print "All written!"
			break


def process(traceFile, dumpFile):
	print >>sys.stderr, "Starting..."
	dbName = "./db/%s_combined" % saveName
	delegator(traceFile, dumpFile, True, True,  dbName)
	#print >>sys.stderr, "Using new engine"
	#newDb = "./db/%s_newEngine" % saveName
	#delegator(traceFile, dumpFile, True,  True, newDb)
	#dbOpenSend.send_json( { 'status' : 'finished' } )


if __name__ == '__main__':
	if len(sys.argv) != 4:
		usage()
		sys.exit(1)
	saveName = sys.argv[3]
	traceFile = sys.argv[1]
	dumpFile = sys.argv[2]
	process(traceFile, dumpFile)
	
