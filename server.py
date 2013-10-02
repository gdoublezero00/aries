from tornado import ioloop, web, websocket,  httpserver, escape
from tornado.options import define, options
from xml.sax.saxutils import *
import os, sys, signal, urllib, random
import sqlite3, json

define('port', default=11111, help='server listen port.', type=int)
path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'aries.sqlite')
cone = {}

#
# Application
#
class Application(web.Application):
	def __init__(self):
		handlers = [
			(r'/', MainHandler),
			(r'/wsChat', WsChatHandler),
			(r'/wsCanvas', WsCanvasHandler),
		]
		settings = dict(
			template_path = os.path.join(os.path.dirname(__file__), 'templates'),
			static_path = os.path.join(os.path.dirname(__file__), 'static'),
			debug = False,
		)
		web.Application.__init__(self, handlers, **settings)

#
# Main Handler
#
class MainHandler(web.RequestHandler):
	def get(self):
		global db
		cur = db.execute("select * from %s order by 1 desc" % 'myTable')
		logs = []
		for row in cur.fetchall():
			logs.append((row[0], row[1], row[2].encode('utf-8')))
			
		self.render(
			"index.html", 
			title="Realtime Messaging", 
			logs=logs)

#
# WebSocket Handler
#
class WsChatHandler(websocket.WebSocketHandler):
	global db

	def open(self):
		if self not in cone:
			cone[self] = None
	
	def on_close(self):
		if self in cone:
			del cone[self];
		for connection, id in cone.iteritems():
			out = {'state':1, 'clients':len(cone), 'id':id}
			connection.write_message(json.dumps(out))
			
	def on_message(self, message):
		bucket = json.loads(message)
		if (bucket['state'] == 'open'):
			if (bucket.get('value') == None):
				cone[self] = random.randint(1000, 9999)
			else:
				cone[self] = long(bucket['value'])
			for connection, id in cone.iteritems():
				out = {'state':1, 'clients':len(cone), 'id':id}
				connection.write_message(json.dumps(out))
		elif (bucket['state'] == 'message'):
			db.execute("insert into myTable values (null, %d, '%s')" % (cone[self], bucket['value']))
			db.commit()
			for connection, id in cone.iteritems():
				out = {'state':2, 'message':escape(bucket['value']), 'id':cone[self]}
				connection.write_message(json.dumps(out))
		
#
# Canvas Handler (unimplement)
#
class WsCanvasHandler(websocket.WebSocketHandler):
	def open(self):
		if self not in cone:
			cone.append(self)
		for i in cone:
			out = {'state':1, 'clients':len(cone)}
			i.write_message(json.dumps(out))
			
	def on_close(self):
		if self in cone:
			cone.remove(self)
		for i in cone:
			out = {'state':1, 'clients':len(cone)}
			i.write_message(json.dumps(out))
					
#
# Main method
#
def main():
	def signal_handler(signal, frame):
		ioloop.IOLoop.instance().add_callback(shutdown)
		
	def shutdown():
		http_server.stop()

	options.parse_command_line()
	http_server = httpserver.HTTPServer(Application())
	http_server.listen(options.port)
	
	signal.signal(signal.SIGINT, signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	
	ioloop.IOLoop.instance().start()

	
#
# Boot method
#
if __name__ == '__main__':
	db = sqlite3.connect(':memory:')
	cur = db.execute("select * from sqlite_master where type = 'table' and name = '%s'" % 'myTable')
	if cur.fetchone() == None:
		db.execute("create table %s (key integer primary key autoincrement not null, id integer not null, message text)" % 'myTable')
		db.commit()

	main()
