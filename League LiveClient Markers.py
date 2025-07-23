import obsws_python as obs, os, json, time, ssl, asyncio, aiohttp, math, csv
from dotenv import load_dotenv

load_dotenv()

# obs websocket variables
host = "localhost"
port = 4455
password = os.getenv("OBS_WEBSOCKET")

# league api URLs
ALLDATA = "https://127.0.0.1:2999/liveclientdata/allgamedata"
EVENTDATA = "https://127.0.0.1:2999/liveclientdata/eventdata"

# initialize variables
LOGPATH = 'D:/Videos/League_VODs/Scripts/log.txt'
EVENTPATH = 'D:/Videos/League_VODs/Scripts/events.csv'
user = ''
champ = ''
gamemode = ''
outputState = ''
outputPath = ''

cl = obs.ReqClient(host=host, port=port, password=password)
ev = obs.EventClient(host=host, port=port, password=password)
print("OBS websocket clients created")

if os.path.exists(LOGPATH):
    with open(LOGPATH, 'a') as log:
        log.write(f'[{time.strftime("%H:%M:%S %p", time.localtime())}]: OBS websocket clients created\n')
else:
    with open(LOGPATH, 'w') as log:
        log.write(f'[{time.strftime("%H:%M:%S %p", time.localtime())}]: OBS websocket clients created\n')

# custom ssl context for League API
ssl_context = ssl.create_default_context()
ssl_context.load_verify_locations(cafile='D:/Videos/League_VODs/Scripts/riotgames.pem')

# access league live client API for username & chosen champion
# if it fails (due to connection error or the game not having loaded in yet), try 5 times before returning NA
async def getPlayerInfo():
    for x in range(5):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(ALLDATA, ssl=ssl_context) as response:
                    global gamemode
                    data = await response.json()
                    
                    username = data.get('activePlayer', {}).get('riotIdGameName')

                    # if getPlayerInfo() runs during League's loading screen, the script may get a KeyError
                    # so raise an error to prevent the script from crashing
                    if username == None:
                        raise KeyError

                    champion = [d['championName'] for d in data['allPlayers'] if username in d.values()][0]
                    gamemode = data.get('gameData', {}).get('gameMode')
                    print("All league data received!", username, champion, gamemode)
                    with open(LOGPATH, 'a') as log:
                        log.write(f'[{time.strftime("%H:%M:%S %p", time.localtime())}]: All league data received! {username} {champion} {gamemode}\n')
                    return username, champion
        except aiohttp.client_exceptions.ClientConnectorError:
            print('Error in getPlayerInfo()! League client not open!\n')
            with open(LOGPATH, 'a') as log:
                log.write(f'[{time.strftime("%H:%M:%S %p", time.localtime())}]: Error in getPlayerInfo()! League client not open!\n')
            time.sleep(60)
        except KeyError:
            print('Error in getPlayerInfo()! Has the game loaded in yet?\n')
            with open(LOGPATH, 'a') as log:
                log.write(f'[{time.strftime("%H:%M:%S %p", time.localtime())}]: Error in getPlayerInfo()! Has the game loaded in yet?\n')
            time.sleep(60) # if getPlayerInfo() doesn't work, getEvents() probably won't either. pause script until it goes through successfully
    
    return 'lycn', 'NA'

# access events endpoint
async def getEvents():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(EVENTDATA, ssl=ssl_context) as response:
                data = await response.json()

                print("League event data received!")
                with open(LOGPATH, 'a') as log:
                    log.write(f'[{time.strftime("%H:%M:%S %p", time.localtime())}]: League event data received!\n')
                return data
    except aiohttp.client_exceptions.ClientConnectorError:
        print("Error in getEvents()! League client not open!\n")
        with open(LOGPATH, 'a') as log:
            log.write(f'[{time.strftime("%H:%M:%S %p", time.localtime())}]: Error in getEvents()! League client not open!\n')

# record_state_changed event handler
def on_record_state_changed(data):
    if data.output_state == 'OBS_WEBSOCKET_OUTPUT_STOPPED':
        global outputState 
        global outputPath
        outputState = data.output_state
        outputPath = data.output_path
        with open('log.txt', 'a') as log:
            log.write(f'[{time.strftime("%H:%M:%S %p", time.localtime())}]: Record_state_changed event handler fired! Output state is {outputState}, outputPath is {outputPath}\n')

# check if recording ended, return League events and outputPath
async def isOBSrecording():
    events = {}
    tempEvents = {} # temporary, local variable
    recordStatus = cl.get_record_status().output_active

    ev.callback.register(on_record_state_changed)
    
    while recordStatus == True:
        if outputState == 'OBS_WEBSOCKET_OUTPUT_STOPPED':
            print("Recording stopped!")
            recordStatus = False
            break

        recordStatus = cl.get_record_status().output_active
        print("Is OBS recording?", recordStatus)
        with open('log.txt', 'a') as log:
            log.write(f'[{time.strftime("%H:%M:%S %p", time.localtime())}]: Is OBS recording? {recordStatus}\n')
       
        tempEvents = await getEvents()
        if tempEvents != None:
            events = tempEvents

        with open('log.txt', 'a', newline='') as log:
            log.write(f'[{time.strftime("%H:%M:%S %p", time.localtime())}]: Getting events from League API...\n\n')

        await asyncio.sleep(1)
    
    ev.callback.deregister(on_record_state_changed)

    if len(events) != 0:
        return events, outputPath
    else:
        return 'No events', outputPath

# condition data to be written into .csv     
def filterEvents(eventDict, username, output, champion):
    with open(LOGPATH, 'a', newline='') as log:
        log.write(f'[{time.strftime("%H:%M:%S %p", time.localtime())}]: FilterEvents running! Current events: {eventDict}\n\n')

    firstBlood = json.dumps([x for x in eventDict.get('Events', []) if (x['EventName'] == 'FirstBlood') and (username in x['Recipient'])])
    championKill = json.dumps([x for x in eventDict.get('Events', []) if (x['EventName'] == 'ChampionKill') and username in x['KillerName']])
    multikill = json.dumps([x for x in eventDict.get('Events', []) if (x['EventName'] == 'Multikill') and (username in x['KillerName'])])
    ace = json.dumps([x for x in eventDict.get('Events', []) if (x['EventName'] == 'Ace') and (username in x['Acer'])])
    assists = json.dumps([x for x in eventDict.get('Events', []) if (x['EventName'] == 'ChampionKill') and username in x['Assisters']])
    deaths = json.dumps([x for x in eventDict.get('Events', []) if (x['EventName'] == 'ChampionKill') and (username in x['VictimName'])])
    
    filteredEvents = []

    if len(firstBlood) != 0:
        firstBlood = json.loads(firstBlood)
        filteredEvents += firstBlood
    
    if len(championKill) != 0:
        championKill = json.loads(championKill)
        filteredEvents += championKill
    
    if len(multikill) != 0:
        multikill = json.loads(multikill)
        filteredEvents += multikill
    
    if len(ace) != 0:
        ace = json.loads(ace)
        filteredEvents += ace

    if len(assists) != 0:
        assists = json.loads(assists)
        # update eventName for assists
        for x in assists:
            x.update((k, 'Assist') for k, v in x.items() if v == 'ChampionKill')
        filteredEvents += assists

    if len(deaths) != 0:
        deaths = json.loads(deaths)
        # update eventName for deaths
        for x in deaths:
            x.update((k, 'Death') for k, v in x.items() if v == 'ChampionKill')
        filteredEvents += deaths
    
    # sort events by EventTime
    sortedEvents = sorted(filteredEvents, key = lambda d: d['EventTime'])

    print("Events filtered and sorted!")
    with open(LOGPATH, 'a', newline='') as log:
        log.write(f'[{time.strftime("%H:%M:%S %p", time.localtime())}]: Events filtered and sorted! Current events: {sortedEvents}\n\n')

    # convert 'EventTime' to min:sec, add trailing 0
    min = ''
    sec = ''
    for x in sortedEvents:
        min = math.floor(x['EventTime'] / 60)
        sec = round(x['EventTime'] % 60, 3)
        x.update((k, f'{min:02d}:{sec:06.3f}') for k, v in x.items() if k == 'EventTime')

    # remove unneeded keys in dictionaries
    for d in sortedEvents:
        d.pop('EventID')
        d.pop('VictimName', None)
        d.pop('Assisters', None)
        d.pop('KillerName', None)

    # add output, champion, gamemode to events
    global gamemode
    output = output.split("/")
    for d in sortedEvents:
        d['Champion'] = champion
        d['Filename'] = output[-1]
        d['Gamemode'] = gamemode
    
    # change order of key value pairs
    customOrder = []
    custom_key_order = ['Filename', 'Champion', 'EventName', 'EventTime', 'Gamemode']
    for d in sortedEvents:
        customSort = {k: d[k] for k in custom_key_order}
        customOrder.append(customSort)
    print("\nEvents have been conditioned:", customOrder, "\n")

    with open(LOGPATH, 'a', newline='') as log:
        log.write(f'[{time.strftime("%H:%M:%S %p", time.localtime())}]: Events have been conditioned: {customOrder}\n\n')

    return custom_key_order, customOrder

def writeToFile(fields, event):
    if os.path.exists(EVENTPATH):
        print("Printing events to .csv...")
        with open(EVENTPATH, 'a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames = fields)
            writer.writerows(event)
            writer.writerow({'Filename': '----', 'Champion': '----', 'EventName': '----', 'EventTime': '----', 'Gamemode': '----'}) # divider for new games
    else:
        with open(EVENTPATH, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames = fields)
            writer.writeheader()
            writer.writerows(event)
            writer.writerow({'Filename': '----', 'Champion': '----', 'EventName': '----', 'EventTime': '----', 'Gamemode': '----'}) # divider for new games
    
    print("Wrote events to events.csv!")
    with open(LOGPATH, 'a', newline='') as log:
        log.write(f'[{time.strftime("%H:%M:%S %p", time.localtime())}]: Wrote events to events.csv!\n-------------------\n\n')

async def main():
    user, champ = await getPlayerInfo()
    events, outputPath = await isOBSrecording()

    if events != 'No events':
        fieldnames, events = filterEvents(events, user, outputPath, champ)
        return fieldnames, events
    else:
        return 'No fields', 'No events'

recordStatus = cl.get_record_status().output_active

# if OBS is recording, run async tasks
if (recordStatus):
    with open(LOGPATH, 'a', newline='') as log:
        log.write(f'[{time.strftime("%H:%M:%S %p", time.localtime())}]: OBS is recording! Getting player info...\n')
    fieldnames, events = asyncio.run(main())

    if events != 'No events':
        writeToFile(fieldnames, events)
    else:
        print("No events to write to .csv. Exiting...")
        with open(LOGPATH, 'a', newline='') as log:
            log.write(f'[{time.strftime("%H:%M:%S %p", time.localtime())}]: No events to write to .csv. Exiting...\n')
else:
    with open(LOGPATH, 'a', newline='') as log:
        log.write(f'[{time.strftime("%H:%M:%S %p", time.localtime())}]: OBS not recording! Exiting...\n')
    print("OBS not recording! Exiting...")
    time.sleep(5)