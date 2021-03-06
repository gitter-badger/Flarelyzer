import csv
import socket
import signal
from constants import *
from subprocess import call
from os import unlink as delete
from traceback import print_exc as stacktrace

interesting = {'rubber cap', 'heat core', 'terra mantle', 'steel boots', 'terra legs', 'dreaded cleaver', "butcher's axe", 'mercenary sword',
               'glooth amulet', 'giant shimmering pearl', 'terra amulet', 'terra hood', 'terra boots', 'glooth cape', 'glooth axe',
               'glooth club', 'glooth blade', 'glooth bag', 'green gem', 'skull staff', 'cheese',
               'crown armor', 'royal helmet', 'medusa shield','tower shield', 'giant sword', 'sacred tree amulet',
               'zaoan armor', 'zaoan helmet', 'zaoan legs', 'zaoan shoes',
               'deepling squelcher', 'deepling staff', 'necklace of the deep', 'ornate crossbow', 'guardian axe',
               'foxtail', 'heavy trident', "warrior's shield", "warrior's axe"
               }

notif_time = 2  # in seconds


with open('Database/pluralMap.csv', mode='r') as pluralFile:
    csvFile = csv.reader(pluralFile)
    pluralMap = {row[0]: row[1] for row in csvFile}
    print 'pluralMap loaded'

sockfile = '/tmp/flarelyzer.sock'


def notify(title, msg):
    call(['notify-send', '--urgency=low', '--expire-time=' + str(notif_time * 1000), title, msg])


def quit():
    global sockfile
    try:
        print 'stopping memory scanner'
        client.sendall('QUIT')
        client.close()
    except: pass
    notify('Flarelyzer', 'Closed!')
    delete(sockfile)
    print '--Notification agent closed--'
    exit(0)


signal.signal(signal.SIGTERM, lambda x, y: quit)


def process_loot(loot):
    try:
        loot = map(lambda x: x[1:], loot)
        loot_amounts = dict()
        for i in xrange(len(loot)):
            lootables = loot[i].split()
            if not lootables:
                #print 'skipping strange loot message: ', lootables
                continue
            loot_start = lootables[0]
            if loot_start.isdigit():
                loot[i] = loot[i][loot[i].find(' ') + 1:]
                if loot[i] in pluralMap:
                    loot[i] = pluralMap[loot[i]]
                else:
                    for suffix in plural_suffixes:
                        if loot[i].endswith(suffix):
                            loot[i].replace(suffix, plural_suffixes[suffix])
                            break
                    else:
                        for word in plural_words:
                            if loot[i].startswith(word):
                                loot[i].replace(word, plural_words[word])
                                break
                loot_amounts[loot[i]] = loot_start
            else:
                if loot_start in ['a', 'an']:
                    loot[i] = loot[i][loot[i].find(' ') + 1:]
                loot_amounts[loot[i]] = '0'
        return loot, loot_amounts
    except:
        print 'loot parser error!'
        stacktrace()

interesting = set(map(str.lower, interesting))
print 'Creating temporary socket file...'
agent = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
agent.bind(sockfile)
agent.listen(1)
print 'waiting for client...'
client, addr = agent.accept()
try:
    while True:
        full_msg = client.recv(1024)
        client.sendall('ACK')
        if full_msg == 'ATTACHED':
            notify('Flarelyzer', 'Started successfully!')
            continue
        elif full_msg == 'NEXT':
            continue
        typeInd = full_msg.find('Loot of ') + 8
        monsterInd = typeInd
        if full_msg.find('a', typeInd) == -1:  # Not a valid loot message
            #print 'skipping invalid loot message: ', full_msg
            continue
        elif full_msg[typeInd] == 'a':  # not an 'a' if its the loot of a boss
            monsterInd = typeInd + 2
        monster = full_msg[monsterInd:full_msg.rfind(':')]
        loot = full_msg[full_msg.rfind(':') + 1:].split(',')
        loot, loot_amounts = process_loot(loot)
        loot = map(str.lower, loot)
        valuables = interesting.intersection(loot)
        if valuables:
            lootmsg = ''
            for v in valuables:
                if loot_amounts[v] != '0':
                    lootmsg += loot_amounts[v] + ' '
                lootmsg += v.title() + ', '
            else:
                lootmsg = lootmsg[:-2]
            notify(monster.title(), lootmsg)
except:
    print 'Notification agent error!'
    stacktrace()
finally:
    quit()
