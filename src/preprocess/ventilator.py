# This file starts the worker processes and distributes tasks to those.
# Also acts as a sort of "manager" process, sending shutdown signals when 
# the analysis is finished.

import sys
sys.path.append(".")
sys.path.append("./src")
import os
from data_sources import *
from threading import Lock
from time import time as systemtime
from pymongo import Connection as MongoClient
import multiprocessing
import time

import worker_process

def usage():
	print >>sys.stderr, "%s <trace file> <memorys snapshot> <savename>" % sys.argv[0]

import zmq
context = zmq.Context()
client = MongoClient()

#Port 5559 is used to signal to workers the memory dump to open
workerControl = context.socket(zmq.PUB)

#Port 5555 is used to send the data to worker processes
sendSocket = context.socket(zmq.PUSH)

#Port 5557 is used to receive the ready signal from the result sink
readySignalRecv = context.socket(zmq.SUB)


def initConnections():
	global workerControl, dbOpenSend, sendSocket, readySignalRecv
	log("Binding to workercontrol")
	workerControl.bind("tcp://127.0.0.1:5559")
	time.sleep(2)

	log("Binding to sendSocket")
	sendSocket.bind("tcp://127.0.0.1:5555")

	log("Connecting to readySignalRecv")
	readySignalRecv.bind("tcp://127.0.0.1:5557")
	readySignalRecv.setsockopt(zmq.SUBSCRIBE, "") 

def log(s):
	print time.strftime("%b %d %Y %H:%M:%S"),"[ventilator]",s

def delegator(traceFile, dumpFile, newEngine, suppressErrors, dbName):
	log("Sending message to workers to load the memory dump...")

	workerControl.send_json( {'type' : 'loadDump', 'dump' : dumpFile, 'db' : dbName })
	log("Waiting for connections to settle")
	time.sleep(2)

	log("Starting to send data to workers")
	fp = open(traceFile)
	t = 0
	for line in fp:
		sendSocket.send_json((t, line))
		t += 1

	log("All data has been sent")
	for i in xrange(workerCnt):
		log("Sending quit signal %d" % i)
		sendSocket.send_json( (-1, { 'entriesSent' : t  }))

		poller = zmq.Poller()
		poller.register(readySignalRecv, zmq.POLLIN)
		while True:
			socks = dict(poller.poll())
			if socks.get(readySignalRecv) == zmq.POLLIN:
				message = readySignalRecv.recv_json()
				log("Got quit signal from pid=%d" % message['pid'])
				break

	log("Writing metainfo")
	db = client[dbName]
	db.meta.insert( {'maxTime' : t-1 } )

	log("Adding indexes")
        db.instructions.ensure_index( [ ('time' , 1 ) ] )
        db.reads.ensure_index([ ('addr', 1),  ('time' , 1)] )
        db.writes.ensure_index([ ('addr', 1),  ('time' , 1)] )




def process(traceFile, dumpFile):
	log("Starting...")
	dbName =  saveName
	delegator(traceFile, dumpFile, True, True,  dbName)

workers = None
resultWriterProcess = None

def spawnChildren():
	global workerCnt
	workerCnt = max(1, multiprocessing.cpu_count() )
	log("Using: 1 ventilator process + %d worker processes" % workerCnt)
#	the correct way: (doesn't work due to ZmQ v2 bug)
#	global workers, resultWriterProcess
#	workers = []
#	for i in xrange(workerCnt):
#		workers.append( multiprocessing.Process(target = worker_process.main))	
#
#	for w in workers: w.start()
	for i in xrange(workerCnt):
		os.system("python src/preprocess/worker_process.py&")
	

def waitForChildren():
#	the correct way: (doesn't work due to ZmQ v2 bug)
#	log("Waiting for workers...")
#	for w in workers: w.join()
#
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
