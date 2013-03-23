import cherrypy
import os
from traceparser import *
import json
from threading import Lock
from time import time as systemtime
import leveldb
#t = Trace("binaries/ex3/trace.txt")
oldDB = leveldb.LevelDB("db/memcrypt_oldEngine")
newDB = leveldb.LevelDB("db/memcrypt_newEngine")

t = DataFlow(oldDB)

mh = MemoryHistory(oldDB, newDB)
mh.indexMemoryAccess()


lock = Lock()
class GuiServer(object):
	def index(self):
		raise cherrypy.HTTPRedirect("static/file1.html")
	def getMemJson(self, address, time):
		if not time.isdigit():
			return json.dumps({'error' : "Time format not recognized!"})

		timeSlot = int(time)
		address = int(address)
		res = {}
		res['bytes'] = []
		res['times'] = []
		#XXX: PArse address as well

		with lock:
			for addr in xrange(address,address + 14):
				result = mh.getWithTime(addr, timeSlot)
				if result is None:
					res['bytes'].append(-1)
					res['times'].append(-1)
				else:
					res['bytes'].append(result[0])
					res['times'].append(result[1])
		return json.dumps(res)
	def getInstructions(self, time):
		time = int(time)
		startTime = max(0,time-10)
		with lock:
			t.seek(startTime)
			result = {'disasm' : []}

			for data in t.iterate():
				curTime, eip, instr, changeMatrix = data
				if data[0] == time: break
				result['disasm'].append((curTime, eip, str(instr)))
		return json.dumps(result)
	def dataflow(self, time, address):
		address = int(address)
		time = int(time)
		with lock:
			startTime = systemtime()
			df = BackwardDataFlow(t, None) #XXX: removed memory
			root = df.follow(address, time)
			nodes, edges = root.dump()
			endTime = systemtime()

		graph = "digraph G {\nsize = \"8,4\"\n"
		graph += "/* Took %f seconds */\n" % (endTime-startTime)
		#XXX: We're cheating by using set here, should move into proper engine
		for e in set(edges):
			graph+= '"%s" -> "%s"\n' % (e[1], e[0])
		graph += "}";
		
		return json.dumps({ 'graph' : graph } )

	index.exposed = True
	getMemJson.exposed = True
	getInstructions.exposed = True
	dataflow.exposed = True

current_dir = os.path.dirname(os.path.abspath(__file__))
conf = {'/static': {'tools.staticdir.on': True,
                      'tools.staticdir.dir': os.path.join(current_dir, 'static')}}

#cherrypy.server.socket_host = "0.0.0.0"
cherrypy.quickstart(GuiServer(), config = conf)

