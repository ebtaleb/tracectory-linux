# This file starts all the other processes and distributes tasks to those.
# Also acts as a sort of "manager" process, sending shutdown signals when 
# the analysis is finished.

import sys
sys.path.append(".")
sys.path.append("./src")
import os
from data_sources import *
from threading import Lock
import leveldb
from time import time as systemtime
import multiprocessing
import time

import worker_process
import result_writer

try: import simplejson as json
except ImportError: import json

def usage():
	print >>sys.stderr, "%s <trace file> <memorys snapshot> <savename>" % sys.argv[0]

import zmq
context = zmq.Context()

#Port 5559 is used to signal to workers the memory dump to open
workerControl = context.socket(zmq.PUB)

#Port 5558 is used to signal to the result sink which database to write
#thre results to 
dbOpenSend = context.socket(zmq.REQ)

#Port 5555 is used to send the data to worker processes
sendSocket = context.socket(zmq.PUSH)

#Port 5557 is used to receive the ready signal from the result sink
readySignalRecv = context.socket(zmq.SUB)


def initConnections():
	global workerControl, dbOpenSend, sendSocket, readySignalRecv
	log("Binding to workercontrol")
	workerControl.bind("tcp://127.0.0.1:5559")
	time.sleep(2)

	log("Connecting to dbOpenSend")
	dbOpenSend.connect("tcp://127.0.0.1:5558")

	log("Binding to sendSocket")
	sendSocket.bind("tcp://127.0.0.1:5555")
	log("Connecting to readySignalRecv")
	readySignalRecv.connect("tcp://127.0.0.1:5557")
	readySignalRecv.setsockopt(zmq.SUBSCRIBE, "") 

def log(s):
	print time.strftime("%b %d %Y %H:%M:%S"),"[ventilator]",s

def delegator(traceFile, dumpFile, newEngine, suppressErrors, dbName):
	log("Sending message to workers to load the memory dump...")

	workerControl.send_json( {'type' : 'loadDump', 'dump' : dumpFile })
	log("Asking the result sink to open the database")
	dbOpenSend.send_json( {'status' : 'ok', 'db' : dbName } )	
	reply =  dbOpenSend.recv()
	log("Reply from sink: %s" % reply)
	assert reply == "OK"
	log("Waiting for connections to settle")
	time.sleep(2)

	log("Starting to send data to workers")
	fp = open(traceFile)
	t = 0
	for line in fp:
		sendSocket.send_json((t, line))
		t += 1

	sendSocket.send_json( (-1, { 'entriesSent' : t  }))
	#sendSocket.send_json("READY")
	log("All data has been sent")
	poller = zmq.Poller()
	poller.register(readySignalRecv, zmq.POLLIN)
	while True:
		socks = dict(poller.poll())
		if socks.get(readySignalRecv) == zmq.POLLIN:
			log("Signal received: all data written to DB")
			workerControl.send_json( { 'type' : 'shutdown' } )
			dbOpenSend.send_json( { 'status' : 'finished' } )
			break


def process(traceFile, dumpFile):
	log("Starting...")
	dbName = "./db/%s_combined" % saveName
	delegator(traceFile, dumpFile, True, True,  dbName)

workers = None
resultWriterProcess = None
def spawnChildren():
	workerCnt = max(1, multiprocessing.cpu_count() - 1)
	log("Using: 1 ventilator process + %d worker processes + 1 result sink" % workerCnt)
#	the correct way: (doesn't work due to ZmQ v2 bug)
#	global workers, resultWriterProcess
#	workers = []
#	for i in xrange(workerCnt):
#		workers.append( multiprocessing.Process(target = worker_process.main))	
#
#	resultWriterProcess = multiprocessing.Process( target = result_writer.loop)
#	resultWriterProcess.start()
#	for w in workers: w.start()
	for i in xrange(workerCnt):
		os.system("python src/preprocess/worker_process.py&")
	os.system("python src/preprocess/result_writer.py&")
	

def waitForChildren():
#	the correct way: (doesn't work due to ZmQ v2 bug)
#	log("Waiting for workers...")
#	for w in workers: w.join()
#
#	log("Waiting for result sink...")
#	resultWriterProcess.join()
	log("Waiting for children to exit...")
	time.sleep(2)

if __name__ == '__main__':
	if len(sys.argv) != 4:
		usage()
		sys.exit(1)
	saveName = sys.argv[3]
	traceFile = sys.argv[1]
	dumpFile = sys.argv[2]

	log("Spawning children")
	spawnChildren()

	log("Initializing connections")
	initConnections()
	log("Processing")
	process(traceFile, dumpFile)
	waitForChildren()	
	log("Last line of code, exiting...")
