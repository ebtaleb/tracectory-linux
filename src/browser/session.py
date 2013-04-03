import leveldb
from datastore.DataFlow import DataFlow
import os
from MemoryHistory import *
class TargetTrace:
	def __init__(self, saveName):
		self.oldDB = leveldb.LevelDB("db/%s_oldEngine" % saveName)
		self.newDB = leveldb.LevelDB("db/%s_newEngine" % saveName )
		self.dataflowTrace = DataFlow(self.oldDB, self)
		self.saveName = saveName
		self.dataflowTraceNew = DataFlow(self.newDB, self)
		self.memDumpAddr = 1
		self.mh = MemoryHistory(self)

		#We aren't thread-safe, must use target.getLock() 
		#with all DB access for each request :(
		self.lock = Lock() 
	def getMaxTime(self):
		return int(self.oldDB.Get("maxTime"))	
	def getLock(self):
		return self.lock
	def getDataflowTracer(self, new = False):
		if not new:
			return self.dataflowTrace
		else:
			return self.dataflowTraceNew
	def getMemDumpAddr(self):
		return self.memDumpAddr
	def getDB(self, which):
		if which == "old":
			return self.oldDB
		elif which == "new":
			return self.newDB
		else:
			raise ValueError
	def getInfoHtml(self):
		filename = "db/%s_info.html" % self.saveName
		if not os.path.exists(filename): return "No info"
		return open(filename).read()

	def getMemoryHistory(self):
		return self.mh
