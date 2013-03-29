import sys
sys.path.append(".")
sys.path.append("./src")
import os
import leveldb
from time import time as systemtime
from analysis_funcs import *
#saveName = "t206"
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
def addToList(db, listName, value):
	"""Straghtforward implementation of random-access arrays atop a key-value store """
	count = 0
	try:
		count = int(db.Get("%s_ctr" % listName))
	except KeyError:
		pass

	db.Put("%s_%d" % (listName,count), value)
	db.Put("%s_ctr" % listName, str(count + 1))


def main(db):
	receive = context.socket(zmq.PULL)
	receive.bind("tcp://127.0.0.1:5556")

	controlSender = context.socket(zmq.PUB)
	controlSender.bind("tcp://127.0.0.1:5557")

	writeBuffer = {} #From time to record
	#control_sendI
	t = 0 
	lastTime = -1
	biggestSeen = -1
	while (lastTime == -1) or (biggestSeen<lastTime):
		#Receive the data to buffer
		t, record = receive.recv_json()
		if t == -1:
			#This is a direct message from ventilator
			#that indicates the last t value
			#we should see.
			lastTime = record['lastTime']	
			continue
		biggestSeen = max(biggestSeen, t)
		#print "Writing %d" % t
		if record is not None:
			db.Put("instr_%d" % t, json.dumps(record))
	db.Put("maxTime", str(biggestSeen))
	log.info("Received all info!")

	#Write indexing of memory accesses
	listOperations = 0
	startTime = systemtime()
	for t in xrange(0, lastTime+1):
		try:
			recordJson = db.Get("instr_%d" % t)
		except KeyError:
			continue

		curRecord = json.loads(recordJson)
		changes = curRecord['changes']
		for key in changes.keys():
			if key.isdigit():
				key = int(key)
				addToList(db, "write_%s" % str(key), str(t))
				listOperations += 1

	endTime = systemtime()
	log.info("Analysis finished, %d operations" % listOperations)
	log.info("%f per second" % (lastTime / (endTime-startTime)))
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
