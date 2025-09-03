import os, pandas as pd, datetime, time, math, subprocess
from nicegui import app, ui, run
from moviepy.editor import VideoFileClip

from League_LiveClient_Markers import VODPATH, EVENTPATH, CLIPPATH
minVal = 0
maxVal = 0

app.add_media_files('/thumb', './thumbnails')
app.add_media_files('/champIcons', 'ddragon')
app.add_media_files('/vods', VODPATH)
app.add_media_files('/clips', CLIPPATH)
app.add_static_file(local_file = EVENTPATH, url_path = '/events.csv')

@ui.page('/')
async def homepage():
    with ui.splitter(horizontal = False, limits = (10, 90), value = 85, reverse = True).classes('w-full').props('before-class=overflow-hidden after-class=overflow-hidden') as splitter:
        with splitter.before:
            with ui.tabs().props('vertical').classes('w-full') as tabs:
                vodsTab = ui.tab('VODs', icon='videocam')
                clipsTab = ui.tab('Clips', icon='movie_creation')
        with splitter.after:
            with ui.tab_panels(tabs, value = vodsTab).classes('w-full'):
                with ui.tab_panel(vodsTab):
                    ui.label('Saved VODs').classes('font-bold text-2xl')

                    with ui.element('div').classes('w-full') as vodDiv:
                        with ui.row():
                            ui.space()
                            loadingVod = ui.spinner(size='lg')
                            ui.space()
                    
                    def createVodTable():
                        events = pd.read_csv(EVENTPATH)

                        with vodDiv:
                            loadingVod.delete()
                            games = ui.table(columns = [{'name':'Game', 'label':'Game', 'field':'Filename', 'required': True, 'align': 'left'},
                                                    {'name': 'Icon', 'label': 'Icon', 'field': 'Icon', 'align': 'center'},
                                                    {'name': 'Champion', 'label':'Champion', 'field':'Champion', 'align': 'left'},
                                                    {'name': 'KDA', 'label':'KDA', 'field':'KDA', 'align': 'left'},
                                                    {'name': 'Gamemode', 'label':'Gamemode', 'field':'Gamemode', 'align': 'left'}], rows = []).classes('w-full mb-3 self-center overflow-y-auto')

                            vods = []

                            for file in os.listdir(VODPATH):
                                itemPath = os.path.join(VODPATH, file)
                                if os.path.isfile(itemPath):
                                    vods.append(file)
                        
                            vods.reverse() # vods goes by oldest to newest by default, reverse it

                            for file in vods:
                                if file in events.values:
                                    kills = len(events.loc[(events['Filename'] == file) & (events['EventName'] == 'ChampionKill')])
                                    deaths = len(events.loc[(events['Filename'] == file) & (events['EventName'] == 'Death')])
                                    assists = len(events.loc[(events['Filename'] == file) & (events['EventName'] == 'Assist')])

                                    kda = f'{kills}/{deaths}/{assists}'

                                    champion = events.loc[events['Filename'] == file, 'Champion'].tolist()[0]
                                    if champion == 'MonkeyKing' or champion == 'Monkey King': champion = 'Wukong'

                                    gamemode = events.loc[events['Filename'] == file, 'Gamemode'].tolist()[0]
                                    
                                    # change gamemode names from how they're referred to in the API
                                    if gamemode == 'RUBY' or gamemode == 'RUBY_TRIAL_2': gamemode = 'DOOMBOTS'
                                    elif gamemode == 'CLASSIC': gamemode = 'DRAFT'
                                    elif gamemode == 'CHERRY': gamemode = 'ARENA'

                                    games.add_row({'Filename': file, 'Icon': '', 'Champion': champion, 'KDA': kda, 'Gamemode': gamemode})
                                else:
                                    games.add_row({'Filename': file, 'Icon': 'No events data', 'Champion':'-', 'KDA':'-', 'Gamemode':'-'})                                      
                            
                            for r, row in enumerate(games.rows):
                                with ui.teleport(f'#{games.html_id} tr:nth-child({r+1}) td:nth-child(2)'):
                                    if row['Icon'] != 'No events data':
                                        if row['Champion'] == 'Wukong':
                                            ui.image('/champIcons/MonkeyKing.png').classes('size-8')
                                        # champions with spaces in their names should have them removed
                                        elif ' ' in row['Champion']:
                                            champ = row['Champion'].replace(' ', '')
                                            ui.image(f'/champIcons/{champ}.png').classes('size-8')
                                        # champions with apostrophes in their names should have them removed, and then capitalized
                                        elif "'" in row['Champion']:
                                            champ = row['Champion'].replace("'", '').capitalize()
                                            ui.image(f'/champIcons/{champ}.png').classes('size-8')
                                        else:
                                            ui.image(f'/champIcons/{row["Champion"]}.png').classes('size-8')                       
                            
                            def handle_row_click_VODs(event):
                                clicked_row_data = event.args[1]
                                file = clicked_row_data['Filename']
                                ui.navigate.to(f'/watch/vod/{file}')
                            
                            games.on('rowClick', handle_row_click_VODs)

                    await run.io_bound(createVodTable)

                with ui.tab_panel(clipsTab):
                    ui.label('Saved Clips').classes('font-bold text-2xl')

                    clips = []

                    with ui.element('div').classes('w-full') as clipDiv:
                        with ui.row() as clipPlaceholder:
                            ui.space()
                            ui.label('Generating clip thumbnails...')
                            ui.spinner(size='lg')
                            ui.space()

                    def createThumbnails():
                        if not os.path.exists('./thumbnails'):
                            os.mkdir('./thumbnails')

                        for file in os.listdir(CLIPPATH):
                            itemPath = os.path.join(CLIPPATH, file)

                            if not os.path.isfile(itemPath):
                                continue

                            clips.append(file)

                            fileName = os.path.splitext(file)[0]
                            thumb_path = f'./thumbnails/{fileName}.webp'

                            # skip iteration if thumbnail already exists
                            if os.path.exists(thumb_path):
                                continue

                            with VideoFileClip(itemPath) as clipThumbnail:
                                clipThumbnail.save_frame(thumb_path, t=1)

                            # add new thumbnail as static file
                            app.add_static_file(local_file=thumb_path, url_path=f'thumb/{fileName}.webp')
                        
                        # check if thumbnail has a corresponding clip in folder, if not, delete it
                        for file in os.listdir('./thumbnails'):
                            thumb_path = os.path.join('./thumbnails', file)

                            if not os.path.isfile(thumb_path):
                                continue

                            clipName = os.path.splitext(file)[0]

                            if os.path.exists(thumb_path) and os.path.exists(os.path.join(CLIPPATH, f'{clipName}.mkv')):
                                continue
                            elif os.path.exists(thumb_path) and os.path.exists(os.path.join(CLIPPATH, f'{clipName}.mp4')):
                                continue
                            else:
                                print(f'Removed {thumb_path}')
                                os.remove(thumb_path)

                        clips.reverse() # clips go by oldest to newest by default, reversing

                        with clipDiv:
                            clipPlaceholder.delete()
                            with ui.grid(columns = 3).classes('w-full'):
                                for vid in clips:
                                    with ui.link(target = f'/watch/clip/{vid}').classes('no-underline'):
                                        with ui.card().tight():
                                            vidName = os.path.splitext(vid)[0]
                                            ui.image(f'thumb/{vidName}.webp')
                                            with ui.card_section():
                                                ui.label(vidName)

                    await run.io_bound(createThumbnails)

@ui.page('/watch/vod/{fileName}')
async def watchVOD(fileName: str):
    with ui.splitter(horizontal = False, limits = (10, 90), value = 85, reverse = True).classes('w-full').props('before-class=overflow-hidden after-class=overflow-hidden') as splitter:
        with splitter.before:
            with ui.tabs().props('vertical').classes('w-full'):
                home = ui.tab('Home', icon='home')
                home.on('click', lambda: ui.navigate.to('/'))
        with splitter.after:
            path = f'/vods/{fileName}'
            v = ui.video(path).classes('mx-3 w-full')

            moviepyVid = VideoFileClip(f'{VODPATH}/{fileName}')
            duration = round(moviepyVid.duration)

            def rangeMinMax(event):
                global minVal, maxVal
                minVal = event.value['min']
                maxVal = event.value['max']

                v.seek(minVal)
            
            async def startClip():
                await run.io_bound(clipVideo)
            
            with ui.expansion('Clip!', icon='movie_creation'). classes('mx-3 w-full'):
                with ui.row().classes('w-full'):
                    ui.space()
                    ui.button('Clip', on_click = startClip)

                clipRange = ui.range(min = 0, max = duration, value = {'min' : 0, 'max': 20}, on_change = rangeMinMax).props('label-always').classes('w-full')
                
                ui.label().bind_text_from(clipRange, 'value', 
                                        backward = lambda minConvert: f'{int(math.floor(minConvert["min"]) / 60):02d}:{(minConvert["min"] % 60):02d} to {int(math.floor(minConvert["max"]) / 60):02d}:{(minConvert["max"] % 60):02d}').classes('text-lg self-center')

            events = pd.read_csv(EVENTPATH)

            def handle_row_click(event):
                clicked_row_data = event.args[1]

                time = clicked_row_data['EventTime']

                sec = time.split(':') # time is in min:sec format, convert back to seconds
                sec = [float(item) for item in sec]

                sec[0] = sec[0] * 60 # convert min to sec
                sec[0] += sec[1] # add sec to previously converted min
                v.seek(sec[0])
                v.play()

            if fileName in events.values:
                rows = events.loc[events['Filename'] == fileName]

                filterSelect = ui.select(label = 'Filter Events Table', options = ['ChampionKill', 'Multikill', 'Assist', 'Death'], 
                                        value = ['ChampionKill', 'Multikill', 'Assist', 'Death'], multiple = True).classes('self-center').props('use-chips')

                table = ui.table.from_pandas(rows, pagination=10).classes('self-center mb-3 overflow-y-auto')
                table.on('rowClick', handle_row_click)

                def applyEventFilter():
                    selectedEvents = filterSelect.value

                    rows = events.loc[events['Filename'] == fileName]

                    if set(selectedEvents) == set(['ChampionKill', 'Multikill', 'Assist', 'Death']):
                        table.rows = rows.to_dict('records')
                        table.update()
                    elif selectedEvents == []:
                        table.rows = []
                        table.update()
                    else:
                        filteredRows = rows.loc[rows['EventName'].isin(selectedEvents)]
                        table.rows = filteredRows.to_dict('records')
                        table.update()
                
                filterSelect.on_value_change(applyEventFilter)

            
            with ui.element('div') as notify:
                pass

            def clipVideo():
                with notify:
                    ui.notify('Clipping video...', type='ongoing')

                clippedVid = moviepyVid.subclip(minVal, maxVal)
                now = datetime.datetime.now()
                clipFileName = f'clip_{now.strftime("%Y-%m-%d %H-%M-%S")}.mp4'
                clippedVid.write_videofile(f'{CLIPPATH}/{clipFileName}')
                clippedVid.close()

                app.add_static_file(local_file = f'{CLIPPATH}/{clipFileName}', url_path = f'/clips/{clipFileName}')

                with notify:
                    ui.notify('Clip has been created!', type='positive')
                    time.sleep(2.5)
                    ui.navigate.to(f'/watch/clip/{clipFileName}')

@ui.page('/watch/clip/{fileName}')
async def watchClip(fileName: str):
    with ui.splitter(horizontal = False, limits = (10, 90), value = 85, reverse = True).classes('w-full').props('before-class=overflow-hidden after-class=overflow-hidden') as splitter:
        with splitter.before:
            with ui.tabs().props('vertical').classes('w-full'):
                home = ui.tab('Home', icon='home')
                home.on('click', lambda: ui.navigate.to('/'))
        with splitter.after:
            path = f'/clips/{fileName}'
            ui.video(path).classes('mx-3 w-full')

            def highlightVideo():
                absolutePath = f'{os.path.abspath(CLIPPATH)}\{fileName}'
                print(path)

                if os.path.exists(absolutePath):
                    cmd = f'explorer /select,"{absolutePath}"'
                    subprocess.run(cmd, shell=True, check=True) # ignore if it returns exit status 1
                else:
                    print('File not found')
            
            with ui.row().classes('w-full'):
                ui.space()
                ui.button('Open Clip in Explorer', on_click=highlightVideo)
                ui.space()

ui.run(title='LiveClient GUI', reload=False, native=True, window_size=(1600, 950), dark = True)