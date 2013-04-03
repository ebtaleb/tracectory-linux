import sys
sys.path.append(".")
sys.path.append("./src")
import os
import leveldb
from time import time as systemtime
#from analysis_funcs import *
import multiprocessing
import zmq
import logging

log = logging.getLogger()
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))
try:
	import simplejson as json
except ImportError:
	import json


context = zmq.Context()
listCounters = {}

def addToList(batch, listName, value):
	global listCounters
	try:
		count = listCounters[listName]
	except KeyError:
		count = 0
	batch.Put("%s_%d" % (listName, count), str(value))
	listCounters[listName] = count + 1	
def writeListCounts(db):
	global listCounters
	batch = leveldb.WriteBatch()
	for key, value in listCounters.items():
		batch.Put("%s_ctr" % key, str(value))
	db.Write(batch, sync = True)

def main(db):
	receive = context.socket(zmq.PULL)
	receive.bind("tcp://127.0.0.1:5556")

	controlSender = context.socket(zmq.PUB)
	controlSender.bind("tcp://127.0.0.1:5557")

	t = 0 
	entriesSent = -1
	biggestSeen = -1

	#The entriesSent change should fix a race condition, not tested yet

	batch = leveldb.WriteBatch()
	count = 0
	while (entriesSent == -1) or (count<entriesSent):
		#Receive the data to buffer
		t, record = receive.recv_json()
		if t == -1:
			#This is a direct message from ventilator
			#that indicates the last t value
			#we should see.
			entriesSent = record['entriesSent']	
			continue
		count += 1
		biggestSeen = max(biggestSeen, t)
		if record is not None:	batch.Put("instr_%d" % t, json.dumps(record))

		if (t%100000)==0: #Batch the writes into groups of 100k
			db.Write(batch)
			batch = leveldb.WriteBatch()
			
	db.Write(batch, sync = True)
	db.Put("maxTime", str(biggestSeen))
	log.info("Received all info!")

	#Write indexing of memory accesses
	startTime = systemtime()

	batch = leveldb.WriteBatch()
	for t in xrange(0, entriesSent):
		try:
			recordJson = db.Get("instr_%d" % t)
		except KeyError:
			continue

		curRecord = json.loads(recordJson)
		changes = curRecord['changes']
		for key, values in changes.items():
			if key.isdigit():
				key = int(key)
				addToList(batch, "write_%s" % str(key), str(t))
			for v in values:
				v = str(v)
				if v.isdigit():
					addToList(batch, "read_%s" % str(v), str(t))
		if (t%100000) == 0: #Batch update sinto groups of 100k
			db.Write(batch)
			batch = leveldb.WriteBatch()
	db.Write(batch)
	writeListCounts(db)	
	endTime = systemtime()
	log.info("%f per second" % (entriesSent / (endTime-startTime)))
	controlSender.send("FINISH")

def waitForControl():
	""" Waits for an instruction to open a database for writing """
	socket = context.socket(zmq.REP)
	socket.bind("tcp://127.0.0.1:5558")
	msg =  socket.recv_json()
	if msg['status'] == 'finished':
		print "Finished"
		return None

	db = leveldb.LevelDB(msg['db'])
	socket.send("OK")
	return db

if __name__ == '__main__':
	while True:
		db = waitForControl()
		if db is None:
			break
		main(db)
