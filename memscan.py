import re
import sys
import socket
from subprocess import check_output, CalledProcessError
import signal
#import time
#TODO: stop opening and closing files with every iteration

cached_loot_messages = set()
notifier = None


def is_timestamp(string):
	return string[2] == ':' and string[:2].isdigit() and string[3:5].isdigit() and string[5] == ' '

#@profile
def messages(chunk):
	index = 0
	while index < len(chunk) - 6:  # No point in reading something shorter than '00:00 '
		if is_timestamp(chunk[index: index + 6]):
			endPos = chunk.find('\0', index + 6)
			yield chunk[index:endPos]
			index = endPos + 1
		else:
			index += 1

#@profile
def read_process_memory(pid):
	global lootRe
	item_drops = []
	exp = dict()
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
				for log_message in messages(chunk):
					#print log_message
					if log_message[5:14] == ' Loot of ':
						global cached_loot_messages
						if log_message in cached_loot_messages:
							continue
						cached_loot_messages.add(log_message)
						item_drops.append(log_message)
					elif log_message[5:17] == ' You gained ':
						t = log_message[0:5]
						try:
							e = int(log_message[17:log_message.find(' ')])
							if t not in exp: exp[t] = e
							else: exp[t] += e
						except: pass
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
	try:
		notifier.close()
	except: pass
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
					notifier.recv(8)
				#print 'time spent reading memory: ', spent
				notifier.sendall('NEXT')
				response = notifier.recv(8)
				if response == 'QUIT':
					quit()
			except Exception, e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				print str(e)
				print str(exc_type) + ' - at line: ' + str(exc_tb.tb_lineno)
				quit()
	print '==Aborting=='
	exit(1)

if __name__ == '__main__':
	main()

