import obsws_python as obs, os, json, time, asyncio, aiohttp, math, polars as pl, keyring, sqlite3, send2trash
from pynput import keyboard
from keyring.backends.Windows import WinVaultKeyring

keyring.set_keyring(WinVaultKeyring())

# league api URLs
ALLDATA = 'https://127.0.0.1:2999/liveclientdata/allgamedata'
EVENTDATA = 'https://127.0.0.1:2999/liveclientdata/eventdata'

# initialize variables
VODPATH = './vods/'
LOGPATH = f"./data/logs/log {time.strftime('%m-%d-%Y')}.txt"
EVENTPATH = './data/events.csv'
DBPATH = './data/data.db'
SETTINGSPATH = './data/settings.json'
CLIPPATH = './clips/'

user = ''
champ = ''
gamemode = ''
outputState = ''
outputPath = ''
recordingDelay = 0
customMarkers = []

# obs websocket variables
host = "localhost"

# for OBS portable
if os.path.exists('./obs/config/obs-studio/plugin_config/obs-websocket'):
    with open('./obs/config/obs-studio/plugin_config/obs-websocket/config.json', 'r') as f:
        config = json.load(f)

        port = int(config.get('server_port'))
        password = config.get('server_password')
# if the user doesn't have OBS portable
else:
    port = keyring.get_password('LiveClient', 'port')
    password = keyring.get_password('LiveClient', 'websocketPassword')
    
    # change port from None because obsws will raise an error since it can't cast None to int
    if port == None: port = 0

# hotkey for custom event marker
def customMarker():
    global customMarkers
    logger.info('Hotkey pressed!')
    currentRecordingTime = cl.get_record_status().output_duration / 1000
    customMarkers.append({'EventName': 'Custom', 'EventTime': currentRecordingTime})
    logger.info('Current time in recording is %s. customMarkers = %s', currentRecordingTime, customMarkers)

listener = keyboard.GlobalHotKeys({'<ctrl>+<F1>': customMarker})

# access league live client API for username & chosen champion
# if it fails 5 times due to a connection error (specifically the League Client not being open), try 5 times before returning username from settings (or a hardcoded one if it wasn't saved beforehand), and NA
async def getPlayerInfo():
    global gamemode
    global recordingDelay
    connectorErrorCounter = 0

    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(ALLDATA, ssl=False) as response:
                    data = await response.json()
                    
                    username = data.get('activePlayer', {}).get('riotIdGameName')
                    tagline = data.get('activePlayer', {}).get('riotIdTagLine')
                    events = data.get('events', {}).get('Events', [])

                    # if getPlayerInfo() runs during League's loading screen, the script may get a KeyError, so raise an error to prevent the script from crashing
                    # prevent the function from continuing if there's no events either, since the loading screen ending is signified by a 'GameStart' event
                    if username == None or len(events) == 0:
                        logger.info('getPlayerInfo() conditions not satisfied. Username = %s#%s and events = %s', username, tagline, events)
                        raise KeyError
                    else:
                        champion = [d['championName'] for d in data['allPlayers'] if username in d.values()][0]
                        gamemode = data.get('gameData', {}).get('gameMode')

                        if len(events) <= 2:
                            recordingDelay = (cl.get_record_status().output_duration / 1000) - 2 # outputDuration is in milliseconds, convert to sec
                            logger.info('Accounted for delay in recording due to the loading screen. It is currently %s seconds into the recording!', recordingDelay + 2)
                        else:
                            # if there are more than two events already available in the API (one of them should be GameStart), it's most likely that we're rejoining a game, so don't account for any delay
                            recordingDelay = 0
                            logger.info("More than two events detected, recording delay wasn't calculated.\n")

                        logger.info('All League data received! %s#%s %s %s\n', username, tagline, champion, gamemode)

                        # store username, in case getPlayerInfo() fails in the future
                        if (os.path.exists(SETTINGSPATH)):
                            with open(SETTINGSPATH, mode = 'r', encoding = 'utf8') as f:
                                settings = json.load(f)

                            if settings.get('username') != username:
                                with open(SETTINGSPATH, mode = 'w', encoding = 'utf8') as f:
                                    settings.update({'username': username, 'tagline': tagline})
                                    json.dump(settings, f)
                        else:
                            with open(SETTINGSPATH, mode = 'w', encoding = 'utf8') as f:
                                settings = {'username': username, 'vodFolderSizeLimit': 50}
                                json.dump(settings, f)
                                
                        return username, champion
        except aiohttp.client_exceptions.ClientConnectorError:
            logger.error('Error in getPlayerInfo()! League client not open!')
            connectorErrorCounter += 1
            
            if connectorErrorCounter == 4:
                if (os.path.exists(SETTINGSPATH)):
                    with open(SETTINGSPATH, mode = 'r', encoding = 'utf8') as f:
                        settings = json.load(f)
                        return settings.get('username'), 'NA'
                else: return 'lycn', 'NA' # if the user's username wasn't stored beforehand, not much can be done. last resort so that the script doesn't crash
            
            time.sleep(10)
        except KeyError:
            logger.warning('Error in getPlayerInfo()! Has the game loaded in yet?')
            time.sleep(1) # if getPlayerInfo() doesn't work, getEvents() probably won't either. pause the script until it goes through successfully

# access events endpoint
async def getEvents():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(EVENTDATA, ssl=False) as response:
                data = await response.json()
                return data
    except aiohttp.client_exceptions.ClientConnectorError:
        logger.error('Error in getEvents()! League client not open!')

# record_state_changed event handler
def on_record_state_changed(data):
    if data.output_state == 'OBS_WEBSOCKET_OUTPUT_STOPPED':
        global outputState 
        global outputPath
        outputState = data.output_state
        outputPath = data.output_path
        logger.info('Record_state_changed event handler fired! Output state is %s, outputPath is %s', outputState, outputPath)

# check if recording ended, return League events and outputPath
async def isOBSrecording():
    logOnlyOnce = 0

    events = {}
    tempEvents = {} # temporary, local variable
    recordStatus = cl.get_record_status().output_active

    ev.callback.register(on_record_state_changed)
    
    while recordStatus == True:
        if outputState == 'OBS_WEBSOCKET_OUTPUT_STOPPED':
            logger.info("Recording stopped!\n")
            recordStatus = False
            break

        recordStatus = cl.get_record_status().output_active

        if logOnlyOnce == 0:
            logger.info('Is OBS recording? %s', recordStatus)
            logger.info('Getting events from League API every second...')
       
        tempEvents = await getEvents()
        if tempEvents != None:
            if logOnlyOnce == 0:
                logger.info('League event data received!\n')
            events = tempEvents

        logOnlyOnce = 1
        await asyncio.sleep(1)
    
    ev.callback.deregister(on_record_state_changed)

    if len(events) != 0:
        return events, outputPath
    else:
        return 'No events', outputPath

# condition data
def filterEvents(eventDict, username, output, champion):
    try: 
        if len(eventDict.get('Events', [])) >= 3: logger.info('FilterEvents running! Preview of current events: %s, %s, %s\n', eventDict.get('Events', [])[0], eventDict.get('Events', [])[1], eventDict.get('Events', [])[2])
        else: logger.info('FilterEvents running!')

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

        global customMarkers

        if len(customMarkers) != 0:
            filteredEvents += customMarkers
        
        # sort events by EventTime
        sortedEvents = sorted(filteredEvents, key = lambda d: d['EventTime'])

        if len(sortedEvents) >= 3: logger.info('Events filtered and sorted! Preview of current events: %s, %s, %s\n', sortedEvents[0], sortedEvents[1], sortedEvents[2])
        else: logger.info('Events filtered and sorted!')

        # convert 'EventTime' to min:sec, add trailing 0
        min = ''
        sec = ''
        for x in sortedEvents:
            if x['EventTime'] != 'Custom':
                x['EventTime'] += recordingDelay # add delay to EventTime
                min = math.floor(x['EventTime'] / 60)
                sec = round(x['EventTime'] % 60, 3)
                x.update((k, f'{min:02d}:{sec:06.3f}') for k, v in x.items() if k == 'EventTime')

        # remove unneeded keys in dictionaries
        for d in sortedEvents:
            d.pop('EventID', None)
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
        
        if len(customOrder) >= 3: logger.info('Events have been conditioned. Preview: %s, %s, %s\n', customOrder[0], customOrder[1], customOrder[2])
        else: logger.info('Events have been conditioned.')

        return custom_key_order, customOrder
    except Exception as e:
       logging.exception('')

# move events in .csv to SQLite database
def migrateToSQLite():
    import logging
        
    logger = logging.getLogger(__name__)

    fh = logging.FileHandler(LOGPATH, encoding='utf-8')
    ch = logging.StreamHandler()

    logger.setLevel(logging.DEBUG)
    fh.setLevel(logging.DEBUG)
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(ch)
    logger.addHandler(fh)

    con = sqlite3.connect(DBPATH)
    cur = con.cursor()

    cur.execute("PRAGMA foreign_keys = ON")

    cur.execute('''
        CREATE TABLE IF NOT EXISTS videos(
            Filename TEXT NOT NULL PRIMARY KEY,
            Champion TEXT,
            KDA TEXT,
            Gamemode TEXT,
            Result TEXT,
            Status TEXT DEFAULT 'Active',
            Expires TIMESTAMP DEFAULT NULL
        );
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS events(
            Filename TEXT,
            EventName TEXT,
            EventTime TEXT,
            FOREIGN KEY (Filename) REFERENCES videos(Filename)
                ON DELETE CASCADE
        );
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS favorites( 
            Filename TEXT PRIMARY KEY,
            FOREIGN KEY (Filename) REFERENCES videos(Filename)
                ON DELETE CASCADE
        );
    ''')

    cur.execute('''
        CREATE TRIGGER IF NOT EXISTS setExpireDate 
        AFTER UPDATE OF Status ON videos
        FOR EACH ROW WHEN NEW.Status = 'Trash'
        BEGIN
            UPDATE videos
            SET Expires = date('now', '+7 days')
            WHERE Filename = NEW.Filename;
        END;
    ''')

    cur.execute('''
        CREATE TRIGGER IF NOT EXISTS removeExpireDate 
        AFTER UPDATE OF Status ON videos
        FOR EACH ROW WHEN NEW.Status != 'Trash'
        BEGIN
            UPDATE videos
            SET Expires = NULL
            WHERE Filename = NEW.Filename;
        END;
    ''')

    videoList = []
    
    for file in os.listdir(VODPATH):
        itemPath = os.path.join(VODPATH, file)
        if os.path.isfile(itemPath): videoList.append(file)

    if os.path.exists(EVENTPATH):
        eventsDf = pl.read_csv(EVENTPATH, has_header = True)

        try:
            # populating videos table
            for vod in videoList:
                eventFilter = eventsDf.filter(pl.col('Filename') == vod)

                if len(eventFilter) > 0:
                    champion = eventFilter.item(0, 'Champion')
                    kda = f"{len(eventFilter.filter( pl.col('EventName') == 'ChampionKill' ))}/{len(eventFilter.filter( pl.col('EventName') == 'Death' ))}/{len(eventFilter.filter( pl.col('EventName') == 'Assist' ))}"
                    gamemode = eventFilter.item(0, 'Gamemode')

                    cur.execute(f"""
                        INSERT INTO videos (Filename, Champion, KDA, Gamemode) 
                        VALUES (?, ?, ?, ?)
                    """, (vod, champion, kda, gamemode))
                else:
                    cur.execute(f"INSERT INTO videos (Filename) VALUES (?)", (vod,))

            # populating events table
            cur.executemany("INSERT INTO events VALUES(?, ?, ?)", 
                eventsDf.filter(pl.col('Filename').is_in(videoList)).select('Filename', 'EventName', 'EventTime').rows())

            send2trash.send2trash(EVENTPATH)

            logger.info('Successfully moved existing events to SQLite database!')
        except Exception as e:
            logger.warning("Failed to migrate events to SQLite database: %s", e)
    else:
        try:
            videoTuple = [(vod,) for vod in videoList]
            cur.executemany("INSERT INTO videos (Filename) VALUES (?)", videoTuple)
        except Exception as e:
            logger.warning("Failed to create events table in SQLite database: %s", e)

    if os.path.exists('./data/favoritedVODs.csv'):
        try:
            favorites = set(pl.read_csv('./data/favoritedVODs.csv', has_header = True)['Name'].unique().to_list())
            favorites = list(favorites.intersection(videoList))
            favsInFolder = [(fav,) for fav in favorites]

            cur.executemany("INSERT INTO favorites VALUES(?)", favsInFolder)
            logger.info('Successfully moved existing favorites to SQLite database!')

            send2trash.send2trash('./data/favoritedVODs.csv')
        except Exception as e:
            logger.warning('Failed to migrate favorites to SQLite database: %s', e)

    con.commit()

# write events to database (or csv if migration failed)
async def writeToFile(event):
    if os.path.exists(EVENTPATH):
        data = pl.DataFrame(event)

        with open(EVENTPATH, mode = 'w', encoding = 'utf8') as f:
            data.write_csv(f, include_header = True)
    else:
        eventDf = pl.DataFrame(event)

        filename = eventDf.item(0, 'Filename')
        champion = eventDf.item(0, 'Champion')
        kda = f"{len(eventDf.filter( pl.col('EventName') == 'ChampionKill' ))}/{len(eventDf.filter( pl.col('EventName') == 'Death' ))}/{len(eventDf.filter( pl.col('EventName') == 'Assist' ))}"
        gamemode = eventDf.item(0, 'Gamemode')
        result = None

        # jade = league classic, which isn't accessible thru riot's API
        if gamemode not in {'PRACTICETOOL', 'JADE'}:
            with open(SETTINGSPATH, mode = 'r', encoding = 'utf-8'):
                settings = json.load(f)
                username = settings.get('username')
                tagline = settings.get('tagline')
                puuid = settings.get('puuid')

            if puuid is None:
                if None in {username, tagline}: result = None
                else:
                    async with aiohttp.ClientSession() as session:
                        async with session.post("https://cxnf2smlr4hax5zunln6dte5iq0sobsi.lambda-url.us-east-2.on.aws/getpuuid", json = {"username": username, "tagline": tagline}, headers = {"Content-Type": "application/json"}) as response:
                            if response.status == 200:
                                puuid = response.json()['result']

                                with open(SETTINGSPATH, mode = 'w', encoding = 'utf-8') as f:
                                    settings.update({'puuid': puuid})
                                    json.dump(settings, f)

                                logger.info("Got user's PUUID from Riot API: %s")

            async with aiohttp.ClientSession() as session:
                async with session.post("https://cxnf2smlr4hax5zunln6dte5iq0sobsi.lambda-url.us-east-2.on.aws/getmatchresult", json = {"puuid": puuid}):
                    if response.status == 200: result = response.json()['result']
            
        cur.execute("INSERT INTO videos VALUES(?, ?, ?, ?, ?, ?)", (filename, champion, kda, gamemode, result))
        cur.executemany("INSERT INTO events VALUES(:Filename, :EventName, :EventTime)", event)
        con.commit()
    
    logger.info('Events saved!')

# delete events for VODs that are no longer saved
def delEvents(vodPath, eventPath):
    # assign filenames of vods in folder to list
    vods = []
    for file in os.listdir(vodPath):
        itemPath = os.path.join(vodPath, file)
        if os.path.isfile(itemPath):
            vods.append(file)

    if os.path.exists(EVENTPATH):
        data = pl.read_csv(eventPath)
        filteredData = data.filter(pl.col('Filename').is_in(vods))

        with open(eventPath, mode = 'w', encoding = 'utf8') as f:
            filteredData.write_csv(f, include_header = True)
    else:
        data = pl.read_database(f"SELECT * FROM events WHERE Filename NOT IN {tuple(vods)}", connection = con)['Filename'].to_list()

        if len(data) == 1:
            data = data[0]
            cur.execute(f"DELETE FROM events WHERE Filename = '{data}'")
        elif len(data) > 1: cur.execute(f"DELETE FROM events WHERE Filename IN {tuple(data)}")

    logger.info("Deleted events that don't exist in VODs folder (if any!)\n-------------------\n")

async def main():
    user, champ = await getPlayerInfo()
    events, outputPath = await isOBSrecording()

    if events != 'No events':
        fieldnames, events = filterEvents(events, user, outputPath, champ)
        await writeToFile(events)
        return fieldnames, events
    else:
        return 'No fields', 'No events'

if __name__ == '__main__':
    import logging
    
    logger = logging.getLogger(__name__)

    con = sqlite3.connect(DBPATH)
    cur = con.cursor()

    os.makedirs('./data/logs', exist_ok = True)

    fh = logging.FileHandler(LOGPATH, encoding='utf-8')
    ch = logging.StreamHandler()

    logger.setLevel(logging.DEBUG)
    fh.setLevel(logging.DEBUG)
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(ch)
    logger.addHandler(fh)

    try:
        migrateToSQLite()

        cl = obs.ReqClient(host=host, port=port, password=password)
        ev = obs.EventClient(host=host, port=port, password=password)

        logger.info('OBS websocket client created successfully.')

        recordStatus = cl.get_record_status().output_active

        # if OBS is recording, run async tasks
        if (recordStatus):
            logger.info('OBS is recording! Getting player info...')
            listener.start()
            fieldnames, events = asyncio.run(main())

            if events != 'No events':
                delEvents(VODPATH, EVENTPATH)
            else:
                logger.info('No events to save. Opening GUI...')
        else:
            logger.info('OBS not recording! Opening GUI...\n-------------------\n')
    except ConnectionRefusedError:
        if os.path.exists('./obs/config/obs-studio/plugin_config/obs-websocket'): logger.critical('OBS Websocket refused the connection and LiveClient is unable to continue. Did you set up Websocket in OBS Portable?\n-------------------\n')
        else: logger.critical('OBS Websocket refused the connection and LiveClient is unable to continue. Make sure you entered the correct OBS Websocket port and password in Settings!\n-------------------\n')