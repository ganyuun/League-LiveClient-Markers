import os, pandas as pd, datetime, math
from nicegui import app, ui
from League_LiveClient_Markers import VODPATH, EVENTPATH
from moviepy.editor import VideoFileClip

CLIPPATH = '../../Clips'
minVal = 0
maxVal = 0

app.add_media_files('/vods', VODPATH)
app.add_media_files('/clips', CLIPPATH)
app.add_static_file(local_file = EVENTPATH, url_path = '/events.csv')

@ui.page('/', dark = True)
def homepage():
    with ui.splitter(horizontal = False, limits = (10, 90), value = 85, reverse = True).classes('w-full') as splitter:
        with splitter.before:
            with ui.tabs().props('vertical') as tabs:
                vodsTab = ui.tab('VODs', icon='videocam')
                clipsTab = ui.tab('Clips', icon='movie_creation')
        with splitter.after:
            with ui.tab_panels(tabs, value = vodsTab).classes('w-full'):
                with ui.tab_panel(vodsTab):
                    ui.label('VODs in Folder:')
                    vods = []

                    for file in os.listdir(VODPATH):
                        itemPath = os.path.join(VODPATH, file)
                        if os.path.isfile(itemPath):
                            vods.append(file)
                    
                    vods.reverse() # vods goes by oldest to newest by default, reverse it
                    
                    with ui.list():
                        for file in vods:
                            with ui.item():
                                with ui.link(target = f'/watch/vod/{file}'):
                                    ui.item_label(file)
                with ui.tab_panel(clipsTab):
                    ui.label('Clips in Folder:')
                    clips = []

                    for file in os.listdir(CLIPPATH):
                        itemPath = os.path.join(CLIPPATH, file)
                        if os.path.isfile(itemPath):
                            clips.append(file)
                    
                    clips.reverse() # clips go by oldest to newest by default
                    
                    with ui.list():
                        for file in clips:
                            with ui.item():
                                with ui.link(target = f'/watch/clip/{file}'):
                                    ui.item_label(file)

@ui.page('/watch/vod/{fileName}', dark = True)
def watchVOD(fileName: str):
    with ui.splitter(horizontal = False, limits = (10, 90), value = 85, reverse = True).classes('w-full') as splitter:
        with splitter.before:
            with ui.tabs().props('vertical') as tabs:
                with ui.link(target="/").classes('no-underline'):
                    vodsTab = ui.tab('VODs', icon='videocam')
                    clipsTab = ui.tab('Clips', icon='movie_creation')
        with splitter.after:
            path = f'/vods/{fileName}'
            v = ui.video(path)

            moviepyVid = VideoFileClip(f'{VODPATH}/{fileName}')
            duration = round(moviepyVid.duration)

            def rangeMinMax(event):
                global minVal, maxVal
                minVal = event.value['min']
                maxVal = event.value['max']

                v.seek(minVal)
            
            def clipVideo():
                clippedVid = moviepyVid.subclip(minVal, maxVal)
                now = datetime.datetime.now()
                clippedVid.write_videofile(f'{CLIPPATH}/clip_{now.strftime("%Y-%m-%d %H-%M-%S")}.mp4')
            
            with ui.row().classes('w-full'):
                ui.space()
                ui.button('Clip', on_click = clipVideo)

            clipRange = ui.range(min = 0, max = duration, value = {'min' : 0, 'max': 20}, on_change = rangeMinMax).props('label-always').classes('w-full left-3')
            
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

            if fileName in events.values:
                rows = events.loc[events['Filename'] == fileName]
                table = ui.table.from_pandas(rows).classes('self-center')
                table.on('rowClick', handle_row_click)

@ui.page('/watch/clip/{fileName}', dark = True)
def watchClip(fileName: str):
    with ui.splitter(horizontal = False, limits = (10, 90), value = 85, reverse = True).classes('w-full') as splitter:
        with splitter.before:
            with ui.tabs().props('vertical') as tabs:
                with ui.link(target="/").classes('no-underline'):
                    vodsTab = ui.tab('VODs', icon='videocam')
                    clipsTab = ui.tab('Clips', icon='movie_creation')
        with splitter.after:
            path = f'/clips/{fileName}'
            ui.video(path)

ui.run(title='LiveClient GUI', reload=False, native=True, window_size=(1600, 950))