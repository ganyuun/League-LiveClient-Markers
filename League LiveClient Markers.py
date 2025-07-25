import obsws_python as obs, os, json, time, ssl, asyncio, aiohttp, math, pandas as pd
from dotenv import load_dotenv

load_dotenv()

# obs websocket variables
host = "localhost"
port = 4455
password = os.getenv("OBS_WEBSOCKET")

# league api URLs
ALLDATA = 'https://127.0.0.1:2999/liveclientdata/allgamedata'
EVENTDATA = 'https://127.0.0.1:2999/liveclientdata/eventdata'

# initialize variables
VODPATH = 'D:\Videos\League_VODs'
LOGPATH = 'D:/Videos/League_VODs/Scripts/log.txt'
EVENTPATH = 'D:/Videos/League_VODs/Scripts/events.csv'
user = ''
champ = ''
gamemode = ''
outputState = ''
outputPath = ''

cl = obs.ReqClient(host=host, port=port, password=password)
ev = obs.EventClient(host=host, port=port, password=password)

def log(path, writingMode, msg):
    with open(path, writingMode) as log:
        log.write(f'[{time.strftime("%H:%M:%S %p", time.localtime())}]: {msg}\n')

print("OBS websocket clients created")

if os.path.exists(LOGPATH):
    log(LOGPATH, 'a', 'OBS websocket clients created')
else:
    log(LOGPATH, 'w', 'OBS websocket clients created')

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
                    log(LOGPATH, 'a', f'All league data received! {username} {champion} {gamemode}')
                    return username, champion
        except aiohttp.client_exceptions.ClientConnectorError:
            print('Error in getPlayerInfo()! League client not open!\n')
            log(LOGPATH, 'a', 'Error in getPlayerInfo()! League client not open!')
            time.sleep(60)
        except KeyError:
            print('Error in getPlayerInfo()! Has the game loaded in yet?\n')
            log(LOGPATH, 'a', 'Error in getPlayerInfo()! Has the game loaded in yet?')
            time.sleep(60) # if getPlayerInfo() doesn't work, getEvents() probably won't either. pause script until it goes through successfully
    
    return 'lycn', 'NA'

# access events endpoint
async def getEvents():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(EVENTDATA, ssl=ssl_context) as response:
                data = await response.json()
                print("League event data received!")
                log(LOGPATH, 'a', 'League event data received!')
                return data
    except aiohttp.client_exceptions.ClientConnectorError:
        print("Error in getEvents()! League client not open!\n")
        log(LOGPATH, 'a', 'Error in getEvents()! League client not open!')

# record_state_changed event handler
def on_record_state_changed(data):
    if data.output_state == 'OBS_WEBSOCKET_OUTPUT_STOPPED':
        global outputState 
        global outputPath
        outputState = data.output_state
        outputPath = data.output_path
        log(LOGPATH, 'a', f'Record_state_changed event handler fired! Output state is {outputState}, outputPath is {outputPath}')

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
        log(LOGPATH, 'a', f'Is OBS recording? {recordStatus}')
       
        tempEvents = await getEvents()
        if tempEvents != None:
            events = tempEvents

        log(LOGPATH, 'a', 'Getting events from League API...\n')

        await asyncio.sleep(1)
    
    ev.callback.deregister(on_record_state_changed)

    if len(events) != 0:
        return events, outputPath
    else:
        return 'No events', outputPath

# condition data to be written into .csv     
def filterEvents(eventDict, username, output, champion):
    log(LOGPATH, 'a', f'FilterEvents running! Current events: {eventDict}\n')

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
    log(LOGPATH, 'a', f'Events filtered and sorted! Current events: {sortedEvents}\n')

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
    log(LOGPATH, 'a', f'Events have been conditioned: {customOrder}\n')

    return custom_key_order, customOrder

# write events to csv using pandas
def writeToFile(event):
    data = pd.DataFrame(event)
    divider = {'Filename': '----', 'Champion': '----', 'EventName': '----', 'EventTime': '----', 'Gamemode': '----'}
    divider = pd.DataFrame([divider])
    
    if os.path.exists(EVENTPATH):
        data.to_csv(EVENTPATH, index = False, header = False, mode='a')
        divider.to_csv(EVENTPATH, index = False, header = False, mode='a')
    else:
        data.to_csv(EVENTPATH)
        divider.to_csv(EVENTPATH, index = False, header = False, mode='a')
    
    print("Wrote events to events.csv!")
    log(LOGPATH, 'a', 'Wrote events to events.csv!\n-------------------\n')

# delete events in csv that are no longer in VOD folder
def delEvents(vodPath, eventPath):
    # assign filenames of vods in folder to list
    vods = []
    for file in os.listdir(vodPath):
        itemPath = os.path.join(vodPath, file)
        if os.path.isfile(itemPath):
            vods.append(file)
    vods.append('----') # this is file divider, don't want them to be removed
    
    # filter csv by Filename column
    data = pd.read_csv(eventPath)
    filteredData = data[data['Filename'].isin(vods)]
    filteredData.to_csv(eventPath, index = False)
    log(LOGPATH, 'a', "Deleted events that don't exist in VODs folder (if any)!")

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
    log(LOGPATH, 'a', 'OBS is recording! Getting player info...')
    fieldnames, events = asyncio.run(main())

    if events != 'No events':
        writeToFile(events)
        delEvents(VODPATH, EVENTPATH)
    else:
        print("No events to write to .csv. Exiting...")
        log(LOGPATH, 'a', 'No events to write to .csv. Exiting...')
else:
    print("OBS not recording! Exiting...")
    log(LOGPATH, 'a', 'OBS not recording! Exiting...')
    time.sleep(5)