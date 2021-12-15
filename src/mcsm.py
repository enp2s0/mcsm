#!/usr/bin/python

import socket
import os, os.path
import sys
import json
import shlex

import Log
import GameServer

log = Log.Log()

if len(sys.argv) != 2:
	log.err("mcsm requires exactly one argument, pointing to the server root!")
	sys.exit(1)

def parse_args(argv):
	cfgfile = argv[1]

	return cfgfile

def read_cfg_file(cfgfile):
	log.info(f"reading configuration file '{cfgfile}'...")
	try:
		cf = open(cfgfile)
		config = json.load(cf)
	except Exception as e:
		log.fail("error reading config", e)

	cf.close()
	return config

def make_socket(socketpath):
	log.info(f"creating control socket '{socketpath}'...")

	server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	if os.path.exists(socketpath):
		os.remove(socketpath)
	server.bind(socketpath)

	log.info(f"listening on {socketpath}.")
	return server

cfgfile = parse_args(sys.argv)
config = read_cfg_file(cfgfile)

rootdir = config["mcsm"]["rootdir"]
log.info(f"changing to root directory '{rootdir}'...")
os.chdir(rootdir)

mgr = GameServer.ServerManager(log, config["servers"])
server = make_socket(config["mcsm"]["socket"])

while True:
	server.listen()
	conn, addr = server.accept()
	datagram = conn.recv(1024)

	if datagram:
		cmd = datagram.decode("utf-8")
		tokens = shlex.split(cmd)
		log.info(f"received command: {cmd}")

		if len(tokens) == 0:
			log.warn("client sent meaningless command!")
		elif tokens[0] == "create":
			mgr.create_server(tokens[1], tokens[2])
		elif tokens[0] == "destroy":
			mgr.delete_server(tokens[1])
		elif tokens[0] == "clone":
			mgr.clone_server(tokens[1], tokens[2])
		elif tokens[0] == "start":
			mgr.start_server(tokens[1])
		else:
			log.warn(f"unknown command!")

	else:
		log.warn("client opened socket but sent no data!")

	conn.close()
