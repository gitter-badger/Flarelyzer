import sys
import csv
import socket
import signal
from subprocess import call
from os import unlink as delete
from constants import *
#import time

interesting = {'rubber cap', 'terra mantle', 'steel boots', 'terra legs', 'dreaded cleaver', 'mercenary sword',
               'glooth amulet', 'giant shimmering pearl', 'terra hood', 'terra boots', 'glooth cape', 'glooth axe',
               'glooth club', 'glooth blade', 'glooth bag', 'green gem', 'cheese'
               }

notif_time = 2  # in seconds

with open('Database/pluralMap.csv', mode='r') as pluralFile:
    csvFile = csv.reader(pluralFile)
    pluralMap = {row[0]: row[1] for row in csvFile}
    print 'pluralMap loaded'

sockfile = '/tmp/flarelyzer.sock'


def notify(title, msg):
    call(['notify-send', '--urgency=low', '--expire-time=' + str(notif_time * 1000), title, msg])


def quit(connection=None):
    if connection is not None:
        print 'stopping memory scanner'
        connection.sendall('QUIT')
        connection.close()
    notify('Flarelyzer', 'Closed!')
    global sockfile
    delete(sockfile)
    print '--Notification agent closed--'
    sys.exit(0)


signal.signal(signal.SIGTERM, lambda x, y: quit)

#@profile
def processLoot(loot):
    #print 'before:',loot
    loot = map(lambda x: x[1:], loot)
    #print 'after:',loot
    loot_amounts = dict()
    #timeR = time.time()
    for i in xrange(len(loot)):
        loot_start = loot[i].split()[0]
        if loot_start.isdigit():
            loot[i] = loot[i][loot[i].find(' ') + 1:]
            if loot[i] in pluralMap:
                #print '[pluralMap]replaced ' + loot[i] + ' with ' + pluralMap[loot[i]]
                loot[i] = pluralMap[loot[i]]
            else:
                for suffix in plural_suffixes:
                    if loot[i].endswith(suffix):
                        #print '[pluralSuffix]replaced ' + loot[i] + ' with ',
                        loot[i].replace(suffix, plural_suffixes[suffix])
                        #print loot[i]z
                        break
                else:
                    for word in plural_words:
                        if loot[i].startswith(word):
                            #print '[pluralWords]replaced ' + loot[i] + ' with ',
                            loot[i].replace(word, plural_words[word])
                            #print loot[i]
                            break
            loot_amounts[loot[i]] = loot_start
        else:
            if loot_start in ['a', 'an']:
                loot[i] = loot[i][loot[i].find(' ') + 1:]
            loot_amounts[loot[i]] = '0'
    return loot, loot_amounts
    #print 'time spent reading loot: ', time.time() - timeR


print 'Creating temporary socket file...'
agent = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
agent.bind(sockfile)
agent.listen(1)
print 'waiting for client...'
client, addr = agent.accept()
print 'connected!'
try:
    while True:
        full_msg = client.recv(1024)
        if full_msg == 'ATTACHED':
            notify('Flarelyzer', 'Started successfully!')
            client.sendall('ACK')
            continue
        client.sendall('ACK')
        typeInd = full_msg.find('Loot of ') + 8
        monsterInd = typeInd
        if full_msg[typeInd] == 'a':  # not an 'a' if its the loot of a boss
            monsterInd = typeInd + 2
        monster = full_msg[monsterInd:full_msg.rfind(":")]
        loot = full_msg[full_msg.rfind(':') + 1:].split(',')
        loot, loot_amounts = processLoot(loot)

        valuables = interesting.intersection(loot)
        if valuables:
            lootmsg = ''
            for v in valuables:
                if loot_amounts[v] != '0':
                    lootmsg += loot_amounts[v] + ' '
                lootmsg += v.title() + ', '
            else:
                lootmsg = lootmsg[:-2]
            # print 'notifying: '+lootmsg
            notify(monster.title(), lootmsg)
except Exception, e:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    print 'Notification agent error ' + str(exc_type) + ' - at line: ' + str(exc_tb.tb_lineno)
    client.sendall('QUIT')
finally:
    client.close()
    quit()
