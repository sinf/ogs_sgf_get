#!/usr/bin/env python3
import requests
import json
import os
from time import sleep, time
import sqlite3
from argparse import ArgumentParser
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def is_bot_game(g):
	return g["players"]["white"]["ui_class"] == "bot" \
	or g["players"]["black"]["ui_class"] == "bot"

class OGS_Mirror:

	def __init__(self, db_path, sgf_dir):
		print("SOLite database:", db_path);
		self.db=sqlite3.connect(db_path, isolation_level='IMMEDIATE')
		self.dbc=self.db.cursor()
		self.dbc.execute("CREATE TABLE IF NOT EXISTS response (url TEXT UNIQUE NOT NULL, content TEXT);")
		self.dbc.execute("CREATE TABLE IF NOT EXISTS player_id (name TEXT UNIQUE NOT NULL, id INTEGER);")
		# games table is for conveniently searching downloaded sgf
		self.dbc.execute("CREATE TABLE IF NOT EXISTS games (id INTEGER UNIQUE, playerB TEXT, playerW TEXT, started TEXT, ended TEXT, robot INTEGER);")
		self.min_request_interval = 0.5
		self.sgf_dir = sgf_dir

		strat=Retry(total=5,
			status_forcelist=[429, 500, 502, 503, 504],
			method_whitelist=["HEAD", "GET", "OPTIONS"],
			backoff_factor=5)
		adapter=HTTPAdapter(max_retries=strat)
		self.sess=requests.Session()
		self.sess.mount("http://", adapter)
		self.sess.mount("https://", adapter)
	
	def close(self):
		self.sess.close()
		self.dbc.close()
		self.db.commit()
		self.db.close()
	
	def get_raw(self, url):
		print("GET", url)
		sleep(self.min_request_interval)
		r=self.sess.get(url)
		if r.status_code == requests.codes.ok:
			return r.text
		print("HTTP status", r.status_code)
		return None
	
	def get_cached(self, url):
		for row in self.dbc.execute('SELECT content FROM response WHERE url = ?', (url,)):
			print("from cache:", url)
			return row[0]
		content = self.get_raw(url)
		if content:
			self.dbc.execute("INSERT INTO response (url, content) VALUES (?,?)", (url, content))
		return content

	def get_file(self, url, filepath):
		if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
			os.makedirs(os.path.dirname(filepath), exist_ok=True)
			content=self.get_raw(url).encode("utf8")
			if content:
				with open(filepath,"wb") as f:
					f.write(content)
				print("wrote", len(content), "bytes to file", filepath)
				return True
		return False

	def get_player_id(self, username):
		for row in self.dbc.execute('SELECT id FROM player_id WHERE name = ?', (username,)):
			return int(row[0])
		url="http://online-go.com/api/v1/players?username=" + requests.utils.quote(username,safe='')
		ds=self.get_cached(url);
		i=None
		if ds:
			ds=json.loads(ds)
			i=ds["results"][0]["id"]
			# what if player not found ?
			self.dbc.execute("INSERT INTO player_id (name,id) VALUES (?,?)", (username, i))
		return i

	def get_recent_games(self, pid, limit=-1, quit_early=False):
		page=0
		games_found=0
		games_saved=0
		while limit < 0 or games_found < limit:
			page += 1
			ds = self.get_raw("http://online-go.com/api/v1/players/{}/games?ordering=-id&page={}".format(pid,page))
			if ds is None:
				# we don't know how many pages exist, try them all until 404
				break
			ds = json.loads(ds)
			games = ds["results"]
			new_games_saved = 0
			for g in games:
				if g["mode"] != "game":
					continue
				i=g["id"]
				b=g["players"]["black"]["username"]
				w=g["players"]["white"]["username"]
				started=g.get("started",None)
				ended=g.get("ended",None)
				robot=is_bot_game(g)
				url="http://online-go.com/api/v1/games/{}/sgf".format(i)
				path=os.path.join(self.sgf_dir, "{}-{}-{}.sgf".format(i,b,w))
				if self.get_file(url, path):
					new_games_saved += 1
					self.db.execute("INSERT INTO games (id,playerB,playerW,started,ended,robot) VALUES (?,?,?,?,?,?)",
						(i, b, w, started, ended, robot))
				games_found += 1
				if games_found == limit:
					break
			games_saved += new_games_saved
			print("page", page, "games found", games_found, "saved", games_saved)
			if quit_early and new_games_saved==0:
				break

def main():
	ap=ArgumentParser(prog="sgf_get.py",
		description="""
Fetches at most LIMIT recent games of user USERNAME from online-go.com.
SGF files are saved to directory OUTPUTDIR.
Temporary cruft is saved in DATABASE.
Re-running this script downloads only games that haven't been yet downloaded.
""")
	ap.add_argument("username", metavar="USERNAME", nargs='+', help='Can specify multiple usernames. Case sensitive')
	ap.add_argument("-l", "--limit", metavar="LIMIT", type=int, default=100, help='Use -1 for no limit')
	ap.add_argument("-o", "--outputdir", metavar="OUTPUTDIR", type=str, default='./sgf')
	ap.add_argument("-k", "--keep-going", action='store_true', help='Keep going further into the past even if many games are found to be already downloaded')
	args=ap.parse_args()

	assert type(args.outputdir) is str
	assert type(args.limit) is int

	db_path = os.path.join(args.outputdir, 'sgf_get.db')
	os.makedirs(args.outputdir, exist_ok=True)

	print("Output directory:", args.outputdir)
	print("SQLite database file:", db_path)
	print("Maximum games:", args.limit)

	try:
		api=OGS_Mirror(db_path = db_path, sgf_dir = args.outputdir)

		for username in args.username:
			userid=api.get_player_id(username)
			if userid is None:
				print("user not found:", username)
			else:
				print("fetching games for user", username, "ID:", userid)
				api.get_recent_games(pid = userid, limit = args.limit, quit_early = not (args.keep_going is True))
	except KeyboardInterrupt:
		print("Canceled")
	finally:
		api.close()
		print("Done")

main()

