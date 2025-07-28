import os, pandas as pd, datetime, math, subprocess
from nicegui import app, ui
from League_LiveClient_Markers import VODPATH, EVENTPATH
from moviepy.editor import VideoFileClip

CLIPPATH = '../../Clips'
minVal = 0
maxVal = 0

app.add_media_files('/thumb', './thumbnails')
app.add_media_files('/champIcons', 'ddragon')
app.add_media_files('/vods', VODPATH)
app.add_media_files('/clips', CLIPPATH)
app.add_static_file(local_file = EVENTPATH, url_path = '/events.csv')

@ui.page('/', dark = True)
def homepage():
    with ui.splitter(horizontal = False, limits = (10, 90), value = 85, reverse = True).classes('w-full') as splitter:
        with splitter.before:
            with ui.tabs().props('vertical').classes('w-full') as tabs:
                vodsTab = ui.tab('VODs', icon='videocam')
                clipsTab = ui.tab('Clips', icon='movie_creation')
        with splitter.after:
            with ui.tab_panels(tabs, value = vodsTab).classes('w-full'):
                with ui.tab_panel(vodsTab):
                    ui.label('Saved VODs').classes('font-bold text-2xl')

                    events = pd.read_csv(EVENTPATH)
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

                            gamemode = events.loc[events['Filename'] == file, 'Gamemode'].tolist()[0]

                            games.add_row({'Filename': file, 'Icon': '', 'Champion': champion, 'KDA': kda, 'Gamemode': gamemode}) 
                        else:
                            games.add_row({'Filename': file, 'Icon': 'No events data', 'Champion':'-', 'KDA':'-', 'Gamemode':'-'})
                        
                    for r, row in enumerate(games.rows):
                        with ui.teleport(f'#{games.html_id} tr:nth-child({r+1}) td:nth-child(2)'):
                            if row['Icon'] != 'No events data':
                                ui.image(f'/champIcons/{row["Champion"]}.png').classes('size-8')
                    
                    def handle_row_click_VODs(event):
                        clicked_row_data = event.args[1]
                        file = clicked_row_data['Filename']
                        ui.navigate.to(f'/watch/vod/{file}')
                    
                    games.on('rowClick', handle_row_click_VODs)

                with ui.tab_panel(clipsTab):
                    ui.label('Saved Clips').classes('font-bold text-2xl')

                    clips = []

                    for file in os.listdir(CLIPPATH):
                        itemPath = os.path.join(CLIPPATH, file)

                        if os.path.isfile(itemPath):
                            clips.append(file)
                        
                        if os.path.exists(f'./thumbnails/{file}.webp'):
                            continue
                        else:
                            clipThumbnail = VideoFileClip(os.path.join(CLIPPATH, file))
                            clipThumbnail.save_frame(f'./thumbnails/{file}.webp', t = 1)
                            clipThumbnail.close()
                            app.add_static_file(local_file = f'thumbnails/{file}.webp', url_path = f'thumb/{file}.webp')
                    
                    clips.reverse() # clips go by oldest to newest by default

                    with ui.grid(columns = 3).classes('w-full'):
                        for vid in clips:
                            with ui.link(target = f'/watch/clip/{vid}'):
                                with ui.card().tight():
                                    ui.image(f'thumb/{vid}.webp')
                                    with ui.card_section():
                                        ui.label(vid)

@ui.page('/watch/vod/{fileName}', dark = True)
def watchVOD(fileName: str):
    with ui.splitter(horizontal = False, limits = (10, 90), value = 85, reverse = True).classes('w-full') as splitter:
        with splitter.before:
            with ui.tabs().props('vertical').classes('w-full'):
                with ui.link(target="/").classes('text-white no-underline'):
                    ui.tab('Home', icon='home')
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
            
            def clipVideo():
                ui.notify('Clipping video...', type='ongoing')
                clippedVid = moviepyVid.subclip(minVal, maxVal)

                now = datetime.datetime.now()
                clipFileName = f'clip_{now.strftime("%Y-%m-%d %H-%M-%S")}.mp4'

                clippedVid.write_videofile(f'{CLIPPATH}/{clipFileName}')
                clippedVid.close()
                app.add_static_file(local_file = f'{CLIPPATH}/{clipFileName}', url_path = f'/clips/{clipFileName}')
                ui.navigate.to(f'/watch/clip/{clipFileName}')
                ui.notify('Clip has been created!', type='positive')
            
            with ui.expansion('Clip!', icon='movie_creation'). classes('mx-3 w-full'):
                with ui.row().classes('w-full'):
                    ui.space()
                    ui.button('Clip', on_click = clipVideo)

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
                table = ui.table.from_pandas(rows).classes('self-center mb-3 overflow-y-auto')
                table.on('rowClick', handle_row_click)

@ui.page('/watch/clip/{fileName}', dark = True)
def watchClip(fileName: str):
    with ui.splitter(horizontal = False, limits = (10, 90), value = 85, reverse = True).classes('w-full') as splitter:
        with splitter.before:
            with ui.tabs().props('vertical').classes('w-full'):
                with ui.link(target="/").classes('text-white no-underline'):
                    ui.tab('Home', icon='home')
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


ui.run(title='LiveClient GUI', reload=False, native=True, window_size=(1600, 950))