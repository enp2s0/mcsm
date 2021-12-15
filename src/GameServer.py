import sys
import os
import json
from shutil import copy2, rmtree, copytree

class ServerManager():
	def __init__(self, log, config):
		self.log = log

		self.log.info("creating ServerManager instance...")
		self.config = config

		self.avail_servers = [x for x in os.listdir("servers/") if os.path.isdir("servers/" + x)]
		self.log.info(f"found servers: {self.avail_servers}")

		self.avail_jars = next(os.walk("jars/"), (None, None, []))[2]
		self.log.info(f"found jarfiles: {self.avail_jars}")

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

	def start_server(self, servername):
		servercfg = self.read_server_cfg(servername)

		cmd = f"{servercfg['jvm']} {servercfg['args']} -jar {servercfg['jarfile']}"
		self.log.info(f"starting server: '{cmd}'")

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
