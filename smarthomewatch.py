#!/usr/bin/env python

import argparse,os,sys,subprocess,time,datetime
import pebble as libpebble

import traceback,socket,select,errno

MAX_ATTEMPTS = 5
RELAYS=[False,False,False,False,False,False,False,False,False]
ACTIVERELAY=0

def relayboard(relaynum,state=None):
	result=None

	# Create a socket
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.settimeout(1)
	
	ethrly_ip_address = "10.0.3.6"	# Change to applicable
	ethrly_port = 17494			   # Change to applicable
	try:
		s.connect((ethrly_ip_address,ethrly_port))
		s.setblocking(0)
		
		if state==None:
			cmd=91
		else:
			if state==0:
				cmd=110
			else:
				cmd=100
			if relaynum>0:
				cmd=cmd + relaynum
		s.send(chr(cmd))
		
		canExit=False
		while not canExit:
			rlist, wlist, elist = select.select([ s ], [], [], .1)
			for sock in rlist:
				data = ''
				while True:
					try:
						new_data = sock.recv(1024)
					except socket.error, e:
						if e.args[0] == errno.EWOULDBLOCK:
							# this error code means we would have blocked if the socket was blocking
							break
						raise
					else:
						if not new_data:
							break
						else:
							data += new_data
				if not data:
					canExit=True
				else:
					if cmd==91:
						if relaynum>0:
							print 'relay #'+str(relaynum)+': '+('off','ON')[(ord(data[0]) >> relaynum-1) & 1]
							result=(False,True)[(ord(data[0]) >> relaynum-1) & 1]
						else:
							print 'relays: '+bin(ord(data[0]))+' ['+str(ord(data[0]))+']'
							if ord(data[0])==0:
								result=False
							elif ord(data[0])==255:
								result=True
					else:
						print 'data: '+data
#			if cmd!=91:
			canExit=True
		s.close()
	except socket.timeout:
		print 'timed out'
	print 'result: '+str(result)
	return result

def cmd_remote(pebble):

	def music_control_handler(endpoint, resp):
		global RELAYS
		global ACTIVERELAY
		if resp=="PLAYPAUSE":
			setstate=relayboard(ACTIVERELAY,not RELAYS[ACTIVERELAY])
		elif resp=="PREVIOUS":
			if ACTIVERELAY==0:
				ACTIVERELAY=8
			else:
				ACTIVERELAY-=1
		elif resp=="NEXT":
			if ACTIVERELAY==8:
				ACTIVERELAY=0
			else:
				ACTIVERELAY+=1
		update_metadata()

	def update_metadata():
		artist = ("#%d"%ACTIVERELAY,"all")[ACTIVERELAY==0]
		album = "makr.co"
		state=relayboard(ACTIVERELAY)
		if state!=None:
			RELAYS[ACTIVERELAY]=state
			title=("off","ON")[state]
			try:
				pebble.set_nowplaying_metadata(title, album, artist)
			except:
				print 'error!'

	pebble.register_endpoint("MUSIC_CONTROL", music_control_handler)

	print 'waiting for control events'
	try:
		while True:
			update_metadata()
			if pebble._ser.is_alive():
				print 'alive @'+str(datetime.datetime.now())+'...'
				time.sleep(5)
			else:
				break
	except KeyboardInterrupt:
		pass
	return

def cmd_notification_email(pebble):
	pebble.notification_email("makr.co", "relay board", "ready")

def main():
	parser = argparse.ArgumentParser(description='a utility belt for pebble development')
	parser.add_argument('--pebble_id', type=str, help='the last 4 digits of the target Pebble\'s MAC address. \nNOTE: if \
						--lightblue is set, providing a full MAC address (ex: "A0:1B:C0:D3:DC:93") won\'t require the pebble \
						to be discoverable and will be faster')

	parser.add_argument('--lightblue', action="store_true", help='use LightBlue bluetooth API')
	parser.add_argument('--pair', action="store_true", help='pair to the pebble from LightBlue bluetooth API before connecting.')
	args = parser.parse_args()

	attempts = 0
	while True:
#		if attempts > MAX_ATTEMPTS:
#			raise 'Could not connect to Pebble'
		try:
			pebble_id = args.pebble_id
			if pebble_id is None and "PEBBLE_ID" in os.environ:
				pebble_id = os.environ["PEBBLE_ID"]
			pebble = libpebble.Pebble(pebble_id, args.lightblue, args.pair)

			try:
				cmd_notification_email(pebble)
				cmd_remote(pebble)
			except Exception as e:
				print 'error', e
				pebble.disconnect()
				raise e
				return

			attempts = 0
			pebble.disconnect()
			time.sleep(2)
		except:
			print 'error (2)'
			time.sleep(2)
			attempts += 1

if __name__ == '__main__':
	main()

