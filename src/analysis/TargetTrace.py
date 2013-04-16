import leveldb
from Cycle import *
import os
from MemoryHistory import *

#traces['memcrypt'].memDumpAddr = 0x404050;
#traces['t206'].memDumpAddr = 2771222;
#traces['formatstring'].memDumpAddr = 0x4825A0;

class TargetTrace:
	def __init__(self, saveName):
		if os.path.exists("db/%s_combined" % saveName):
			self.db = leveldb.LevelDB("db/%s_combined" % saveName)
		else:
			raise ValueError, "File not found"
		self.cycleFactory = CycleFactory(self.db, self)
		self.saveName = saveName
		self.memDumpAddr = 0
		try:
			self.memDumpAddr = int(self.db.Get("memDumpAddr"))
		except:
			pass
		self.memory = MemoryHistory(self)

		#We aren't thread-safe, must use target.getLock() 
		#with all DB access for each request :(
		self.lock = Lock() 
	def getMaxTime(self):
		return int(self.db.Get("maxTime"))	
	def getLock(self):
		return self.lock
	def getCycleFactory(self):
		return self.cycleFactory
	def getMemDumpAddr(self):
		return self.memDumpAddr
	def getDB(self):
		return self.db
	def getInfoHtml(self):
		filename = "db/%s_info.html" % self.saveName
		if not os.path.exists(filename): return "No info"
		return open(filename).read()

	def getMemoryHistory(self):
		return self.memory
