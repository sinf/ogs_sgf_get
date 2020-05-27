#!/usr/bin/env python3
import requests
import json
import os
from time import sleep

sess=requests.Session()

def raw_get(url, filepath, skip_read=False):
	if os.path.exists(filepath) and os.path.getsize(filepath)>0:
		if skip_read:
			print("skip", filepath)
			content=""
		else:
			with open(filepath,"rb") as f:
				content=f.read()
			print("read", filepath)
	else:
		print("GET", url)
		xx=sess.get(url)
		content=xx.text
		with open(filepath,"wb") as f:
			f.write(content.encode("utf8"))
		print("saved", filepath)
	return content

def json_get(url, filepath):
	return json.loads(raw_get(url, "./json/"+filepath))

def get_player_id(username):
   url="http://online-go.com/api/v1/players?username=" + username
   ds=json_get(url, "player-{}.json".format(username));
   return ds["results"][0]["id"]
   # Player not found ?

def is_bot_game(g):
	return g["players"]["white"]["ui_class"] == "bot" \
	or g["players"]["black"]["ui_class"] == "bot"

def get_games(pid, count):
	page=1
	gameCount=0
	while gameCount < count:
		ds = json_get("http://online-go.com/api/v1/players/{}/games?ordering=-id&page={}".format(pid, page), "gamelist-{}-{}.json".format(pid,page))
		games = ds["results"]
		for g in games:
			if not is_bot_game(g):
				raw_get(
            	"http://online-go.com/api/v1/games/{}/sgf".format(g["id"]),
					"./sgf/{}-{}-{}.sgf".format(
						g["id"],
						g["players"]["black"]["username"],
						g["players"]["white"]["username"]),
					skip_read=True)
				gameCount += 1
				if gameCount == count:
					break
				sleep(0.2)
		page += 1
		print("games: %d/%d" % (gameCount,count))

def make_dir(d):
	if not os.path.exists(d):
		os.mkdir(d)
		print("created directory", d)

def main():
	make_dir("json")
	make_dir("sgf")
	username=input("Input your username(case sensitive): ")
	try:
		userid=get_player_id(username)
	except:
		print("failed to get user id")
		return
	count=40
	print("player id:", userid)
	print("fetching game list")
	get_games(userid, count)

main()

