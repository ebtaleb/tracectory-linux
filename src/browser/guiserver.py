import cherrypy
import os
import json
from threading import Lock
from time import time as systemtime

from session import TargetTrace
from MemoryHistory import *


traces = {
	't206'     : TargetTrace("t206"),
	'memcrypt' : TargetTrace("qkq")
}

traces['memcrypt'].memDumpAddr = 0x404050;
traces['t206'].memDumpAddr = 2771222;

lock = Lock()
class GuiServer(object):
	def index(self):
		raise cherrypy.HTTPRedirect("static/main.html")
	def getInfo(self):
		target = cherrypy.session['trace']
		return json.dumps( { 

		'maxTime' : target.getMaxTime(),
		'memDumpAddr' : target.getMemDumpAddr()
		} );
	def getMemJson(self, address, time):
		if not time.isdigit():
			return json.dumps({'error' : "Time format not recognized!"})

		timeSlot = int(time)
		address = int(address)
		res = {}
		res['bytes'] = []
		res['times'] = []


		target = cherrypy.session['trace']

		mh = MemoryHistory(target)

		with lock:
			for addr in xrange(address,address + 8*6):
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
		target = cherrypy.session['trace']
		t = target.getDataflowTracer()
		with lock:
			t.seek(startTime)
			result = {'disasm' : []}

			for data in t.iterate():
				curTime, eip, instr, changeMatrix = data
				result['disasm'].append((curTime, eip, str(instr)))
				if data[0] == time: break
		return json.dumps(result)
	def dataflow(self, time, address):
		address = int(address)
		time = int(time)
		target = cherrypy.session['trace']
		t = target.getDataflowTracer()
		with lock:
			startTime = systemtime()
			df = BackwardDataFlow(t)
			root = df.follow(address, time)
			nodes, edges = root.dump()
			endTime = systemtime()

		graph = "digraph G {\n" #size = \"10,20 \"\n"
		graph += "/* Took %f seconds */\n" % (endTime-startTime)
		#XXX: We're cheating by using set here, should move into proper engine
		for e in set(edges):
			graph+= '"%s" -> "%s"\n' % (e[1], e[0])
		graph += "}";
		
		return json.dumps({ 'graph' : graph } )
	def loadTrace(self, trace):
		if not traces.has_key(trace):
			return json.dumps( {'status' : 'error' } )
		cherrypy.session['trace'] = traces[trace]

		return json.dumps( {'status' : 'ok' } )

	index.exposed = True
	getMemJson.exposed = True
	getInfo.exposed = True
	getInstructions.exposed = True
	dataflow.exposed = True
	loadTrace.exposed = True

current_dir = os.path.dirname(os.path.abspath(__file__))
conf = {'/static': {'tools.staticdir.on': True,
                      'tools.staticdir.dir': os.path.join(current_dir, 'static_html')}}

#cherrypy.server.socket_host = "0.0.0.0"
cherrypy.config.update( {"tools.sessions.on": True,
			"tools.sessions.timeout": 60 })
cherrypy.quickstart(GuiServer(), config = conf)

