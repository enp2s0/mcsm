import sys
import os
import json
from shutil import copy2, rmtree, copytree
import shlex
import subprocess
from time import time

class ServerManager():
	def __init__(self, log, config):
		self.log = log

		self.log.info("creating ServerManager instance...")
		self.config = config

		self.avail_servers = [x for x in os.listdir("servers/") if os.path.isdir("servers/" + x)]
		self.log.info(f"found servers: {self.avail_servers}")

		self.avail_jars = next(os.walk("jars/"), (None, None, []))[2]
		self.log.info(f"found jarfiles: {self.avail_jars}")

		# stores all running server objects
		self.running_servers = {}

		needs_start = [s for s in self.avail_servers if self.read_server_cfg(s)["start-on-boot"]]
		self.log.info(f"servers marked for startup: {needs_start}")
		for server in needs_start:
			self.start_server(server)

	def create_server(self, servername, jarname):
		if jarname not in self.avail_jars:
			self.log.warn(f"cannot create '{servername}': jarfile '{jarname}' not available!")
			return None

		if servername in self.avail_servers:
			self.log.warn(f"cannot create '{servername}': server already exists!")
			return None

		jarpath = "jars/" + jarname
		serverpath = "servers/" + servername + "/"

		self.log.info(f"creating server '{servername}' at '{serverpath}'...")
		os.mkdir(serverpath)
		with open(serverpath + "/mcsm_config.json", 'w') as conffile:
			cfg = self.config["defaults"]
			cfg["jarfile"] = jarname
			json.dump(cfg, conffile)

		self.log.info(f"installing jarfile '{jarpath}' to '{servername}'...")
		new_jarpath = serverpath + jarname
		copy2(jarpath, new_jarpath)

		self.log.info(f"signing EULA for '{servername}'...")
		eula = open(serverpath + "eula.txt", "w")
		eula.write("eula=true")
		eula.close()

		self.avail_servers.append(servername)
		self.log.info(f"finished creating server '{servername}'!")
		return servername

	def delete_server(self, servername):
		if servername not in self.avail_servers:
			self.log.warn(f"cannot delete server '{servername}' that does not exist!")
			return None

		serverpath = "servers/" + servername + "/"

		self.log.info(f"removing '{servername}' from server list...")
		self.avail_servers.remove(servername)

		self.log.info(f"deleting directory '{serverpath}'...")
		rmtree(serverpath)

		self.log.info(f"finished deleting server '{servername}'!")
		return servername

	def clone_server(self, oldsrv, newsrv):
		oldpath = "servers/" + oldsrv
		newpath = "servers/" + newsrv

		self.log.info(f"cloning server '{oldsrv}' into '{newsrv}'...")
		copytree(oldpath, newpath)
		self.avail_servers.append(newsrv)
		self.log.info(f"clone into '{newsrv}' complete.")

	# Builds a server object and runs it.
	def start_server(self, servername):
		servercfg = self.read_server_cfg(servername)
		if not servercfg:
			return None

		server_obj = GameServer(self.log, servername, servercfg)
		server_obj.start()
		self.running_servers[servername] = server_obj

	# Runs the update method on all tracked server objects, and deletes stopped ones.
	def update(self):
		needs_del = []
		for name, sobj in self.running_servers.items():
			sobj.update()
			if sobj.dead():
				needs_del.append(name)
		for name in needs_del:
			del self.running_servers[name]

	# Reads the config file for a given server.
	def read_server_cfg(self, servername):
		serverdir = "servers/" + servername + "/"

		try:
			cf = open(serverdir + "mcsm_config.json")
			servercfg = json.load(cf)
			cf.close()
		except Exception as e:
			log.warn(f"could not read config for {servername}: {str(e)}")
			return None

		return servercfg

class GameServer():
	STOPPED = 0
	RUNNING = 1
	STOPPING = 2

	def __init__(self, log, servername, servercfg):
		self.servername = servername
		self.servercfg = servercfg
		self.log = log

		self.jarfile = servercfg["jarfile"]
		self.jvm = servercfg["jvm"]
		self.args = servercfg["args"]

		self.pid = 0
		self.setstate(GameServer.STOPPED)

	# Launch the server executable.
	def start(self):
		server_cmd = f"{self.jvm} {self.args} -jar {self.jarfile}"
		new_cwd = "servers/" + self.servername + "/"
		server_tokens = shlex.split(server_cmd)

		self.log.info(f"starting '{self.servername}': '{server_cmd}'...")
		self.server_process = subprocess.Popen(server_tokens, cwd = new_cwd, stdin = subprocess.PIPE, stdout = subprocess.PIPE, shell = False)
		self.setstate(GameServer.RUNNING)

		self.log.info(f"server '{self.servername}' running as PID {self.server_process.pid}.")
		return self.server_process.pid

	# Stops a server, and sets state to allow for kill if it refuses to stop.
	def stop(self):
		self.server_process.terminate()
		self.state = GameServer.STOPPING

	# Call periodically to monitor the server process and manage state.
	def update(self):
		poll = self.server_process.poll()

		if self.state == GameServer.STOPPED:
			# Nothing to do if the server isn't running, this should never be called anyway.
			pass
		elif self.state == GameServer.RUNNING:
			# If it's running, make sure it hasn't crashed.
			if poll is not None:
				if poll == 0:
					self.log.warn(f"server '{self.servername}' has stopped.")
				else:
					self.log.warn(f"server '{self.servername}' has crashed, exit code {poll}.")

				self.setstate(GameServer.STOPPED)
		elif self.state == GameServer.STOPPING:
			# The server was told to stop but hung, kill it.
			# Set the state again to reset the counter.
			if self.stateage() > 30:
				self.setstate(GameServer.STOPPING)
				self.server_process.kill()


	# Helper functions to read and write the server's IO pipes.
	def send(self, data):
		self.server_process.stdin.write(data)
	def recv(self):
		return self.server_process.stdin.read()

	# State management helpers
	def setstate(self, state):
		self.state = state
		self.last_state_change = time()
	def stateage(self):
		return time() - self.last_state_change
	def dead(self):
		return self.state == GameServer.STOPPED
