import re
import sys
import socket
from subprocess import check_output, CalledProcessError
import signal
#import time
#TODO: stop opening and closing files with every iteration


cached_loot_messages = set()
notifier = None

def read_process_memory(pid):
	global lootRe
	item_drops = []
	exp = dict()
	damage_dealt = dict()
	damage_dealt['You'] = dict()
	maps_file = open("/proc/%s/maps" % pid, 'r')
	mem_file = open("/proc/%s/mem" % pid, 'r')
	try:

		for line in maps_file.readlines():  # for each mapped region
			m = re.match(r'([0-9A-Fa-f]+)-([0-9A-Fa-f]+) ([-r])', line)
			if m.group(3) == 'r':  # if this is a readable region
				start = int(m.group(1), 16)
				end = int(m.group(2), 16)
				mem_file.seek(start)  # seek to region start
				try: chunk = mem_file.read(end - start)  # read region contents
				except: continue
				index = 0
				while True:
					chunkmatch = re.search('([0-9]{2}:[0-9]{2}[^\0]{10,})\0', chunk[index:])
					if chunkmatch is None:
						break
					log_message = chunkmatch.groups()[0]
					if log_message[5:14] == ' Loot of ':
						global cached_loot_messages
						if log_message in cached_loot_messages:
							index += chunkmatch.end()
							continue
						#print 'adding lootmsg:', log_message
						cached_loot_messages.add(log_message)
						item_drops.append(log_message)
					elif log_message[5:17] == ' You gained ':
						t = log_message[0:5]
						try:
							e = int(log_message[17:].split(' ')[0])
							if t not in exp: exp[t] = e
							else: exp[t] += e
						except: pass
					index += chunkmatch.end()
	except KeyboardInterrupt:
		return dict()
	except Exception, e:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		print str(e)
		print 'while reading memory: ' + str(exc_type) + ' - at line: ' + str(exc_tb.tb_lineno)
		return
	finally:
		maps_file.close()
		mem_file.close()

	return_values = dict()
	return_values['item_drops'] = item_drops
	return_values['experience'] = exp
	return return_values


def quit():
	global notifier
	if notifier is not None:
		notifier.close()
	print '--Memory scanner closed--'
	sys.exit(0)

signal.signal(signal.SIGTERM, lambda x, y: quit)


def main():
	global notifier
	sockfile = '/tmp/flarelyzer.sock'
	print 'Initializing memscan...'
	try:
		notifier = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		notifier.connect(sockfile)
		print 'connected to notification server!'
		tibiaPID = check_output(['pgrep', 'Tibia']).split('\n')[0]
		print 'Client PID: ' + str(tibiaPID)
	except socket.error:
		print 'Unable to connect to notification agent!'
		pass
	except CalledProcessError:
		print 'Tibia client not found!'
		pass
	except Exception, e:
		print 'Unexpected error ' + str(e)
	else:
		# we're good to go
		print '===Memory analyzer started==='
		notifier.sendall('ATTACHED')
		while True:
			try:
				#iniT = time.time()
				res = read_process_memory(tibiaPID)
				#spent = time.time() - iniT
				if not res:
					quit()
				for full_msg in res['item_drops']:
					notifier.sendall(full_msg)
					response = notifier.recv(8)
					if response == 'QUIT':
						print 'stopping memory scan upon request'
						quit()
				else:
					pass
					#print 'seconds spent reading memory: ', spent
			except socket.error, e:
				print 'Error passing msg to agent: ' + str(e)
				quit()
			except Exception, e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				print str(e)
				print 'error while reading memory: ' + str(exc_type) + ' - at line: ' + str(exc_tb.tb_lineno)
				quit()
	print '==Aborting=='
	exit(1)

if __name__ == '__main__':
	main()

