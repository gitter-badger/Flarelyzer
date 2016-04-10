import socket
import signal
from time import sleep
from thread import start_new_thread
from traceback import print_exc as stacktrace
from subprocess import check_output, CalledProcessError

cached_loot_messages = set()
heap = tuple()
notifier = None


def update_heap(pid):
	global heap
	while True:
		maps_file = open('/proc/%s/maps' % pid, 'r')
		for line in maps_file.readlines():  # for each mapped region
			mem_info = line.rsplit()
			mapping = mem_info[-1]
			if mapping == '[heap]':  # reading only from the heap, all the messages are allocated there!
				region = mem_info[0].split('-')
				start = int(region[0], 16)
				end = int(region[1], 16)
				if (start, end) != heap:  # check for heap expansions
					heap = (start, end)
		maps_file.close()
		sleep(1)


def is_timestamp(string):
	return string[2] == ':' and string[:2].isdigit() and string[3:5].isdigit() and string[5] == ' '


def messages(chunk):
	index = 0
	while index < len(chunk) - 6:  # No point in reading something shorter than '00:00 '
		if is_timestamp(chunk[index: index + 6]):
			endPos = chunk.find('\0', index + 6)
			yield chunk[index:endPos]
			index = endPos + 1
		else:
			index += 1


def read_process_memory(pid):
	global heap
	mem_file = open('/proc/%s/mem' % pid, 'r')
	item_drops = []
	exp = dict()
	try:
		if not heap:
			start_new_thread(update_heap, (pid,))
			while not heap:
				sleep(0.2)
		start, end = heap
		mem_file.seek(start)
		try:
			chunk = mem_file.read(end - start)  # read region contents
		except:
			chunk = ''
		if messages(chunk):
			for log_message in messages(chunk):
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
	except:
		print 'Error while reading memory!'
		stacktrace()
		return
	finally:
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
	exit(0)

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
	except CalledProcessError:
		print 'Tibia client not found!'
	except:
		print 'Unexpected error'
		stacktrace()
	else:
		# we're good to go
		print '===Memory analyzer started==='
		notifier.sendall('ATTACHED')
		while True:
			try:
				res = read_process_memory(tibiaPID)
				if not res:
					quit()
				for full_msg in res['item_drops']:
					notifier.sendall(full_msg)
					notifier.recv(8)
				notifier.sendall('NEXT')
				response = notifier.recv(8)
				if response == 'QUIT':
					quit()
				sleep(0.1)
			except:
				stacktrace()
				quit()
			sleep(0.1)
	print '==Aborting=='
	exit(1)

if __name__ == '__main__':
	main()
