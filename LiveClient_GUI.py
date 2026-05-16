import os, polars as pl, datetime, math, subprocess, asyncio, json
from platform import system
from nicegui import app, ui, run, background_tasks
from multiprocessing import freeze_support

from League_LiveClient_Markers import VODPATH, EVENTPATH, CLIPPATH, SETTINGSPATH
from DeleteOldVideos import FAVSPATH, delSpecificVid
minVal = 0
maxVal = 0

app.native.window_args['min_size'] = (1200, 650)

if system() == 'Windows': creationFlags = subprocess.CREATE_NO_WINDOW
else: creationflags = 0


app.add_media_files('/thumb', './data/thumbnails')
app.add_media_files('/champIcons', './ddragon')
app.add_media_files('/vods', VODPATH)
app.add_media_files('/clips', CLIPPATH)

if (os.path.exists(EVENTPATH)):
    app.add_static_file(local_file = EVENTPATH, url_path = '/events.csv')
else:
    with open(EVENTPATH, mode = 'w', encoding = 'utf8') as f:
        headers = pl.DataFrame({'Filename': [], 'EventName': [], 'EventTime': [], 'Champion': [], 'Gamemode': []})
        headers.write_csv(f, include_header = True)
    app.add_static_file(local_file = EVENTPATH, url_path = '/events.csv')

if (os.path.exists(FAVSPATH)):
    app.add_static_file(local_file = FAVSPATH, url_path='/favs.csv')
else:
    with open(FAVSPATH, mode = 'w', encoding = 'utf8') as f:
        favVods = pl.DataFrame({'Name': ''})
        favVods.write_csv(f, include_header = True)
    app.add_static_file(local_file = FAVSPATH, url_path='/favs.csv')

if (os.path.exists(SETTINGSPATH)):
    app.add_static_file(local_file = SETTINGSPATH, url_path = '/settings.json')
else:
    with open(SETTINGSPATH, mode = 'w', encoding = 'utf8') as f:
        settings = {'username': '', 'vodFolderSizeLimit': 50}
        json.dump(settings, f)
    app.add_static_file(local_file = SETTINGSPATH, url_path = '/settings.json')

@ui.page('/')
async def homepage():
    with ui.splitter(horizontal = False, limits = (80, 90), value = 85, reverse = True).classes('w-full').props('before-class=overflow-hidden after-class=overflow-hidden') as splitter:
        with splitter.before:
            with ui.tabs().props('vertical').classes('w-full') as tabs:
                vodsTab = ui.tab('VODs', icon='videocam')
                clipsTab = ui.tab('Clips', icon='movie_creation')
                settingsTab = ui.tab('Settings', icon='settings')
        with splitter.after:
            with ui.tab_panels(tabs, value = vodsTab).classes('w-full'):
                with ui.tab_panel(vodsTab):
                    ui.label('Saved VODs').classes('font-bold text-2xl')

                    events = pl.read_csv(EVENTPATH)
                    favVods = pl.read_csv(FAVSPATH)

                    with ui.element('div').classes('w-full') as vodDiv:
                        loadingVod = ui.spinner(size='lg')
                    
                    def handle_item_click_VODs(file):
                        ui.navigate.to(f'/watch/vod/{file}')

                    def handle_button_click_VODS(event, file):
                        favVods = pl.read_csv(FAVSPATH)

                        if file in favVods['Name'].to_list():
                            filteredVods = favVods.filter(pl.col('Name') != file)
                            filteredVods = filteredVods.sort('Name', descending = True)
                            print(f"Removed {file} from favorites. FavVods is now {filteredVods['Name'].to_list()}")
                            event.sender.props('icon=star_border')

                            with open(FAVSPATH, mode = 'w', encoding = 'utf8') as f:
                                filteredVods.write_csv(f, include_header = True)
                        else:
                            newFav = pl.DataFrame({'Name': [file]})
                            favVods = pl.concat([favVods, newFav])
                            favVods = favVods.sort('Name', descending = True)
                            print(f"Added {file} to favorites! FavVods is now {favVods['Name'].to_list()}")
                            event.sender.props('icon=star')

                            with open(FAVSPATH, mode = 'w', encoding = 'utf8') as f:
                                favVods.write_csv(f, include_header = True)
                        
                    def handle_del_button_VODS(file):
                        with ui.dialog() as dialog, ui.card():
                            def delVod(file):
                                if os.path.exists(os.path.join(VODPATH, file)):
                                    ui.notify(f'{file} sent to recycling bin.', type = 'positive')
                                    delSpecificVid(file)
                                    dialog.close()
                                    ui.navigate.reload()
                                else:
                                    ui.notify(f"{file} doesn't exist in specified VOD path.", type = 'negative')

                            ui.label(f'Are you sure you want to delete {file}?')
                            with ui.row().classes('self-center'):
                                ui.button('Yes', color = 'red', on_click = lambda: delVod(file))
                                ui.space()
                                ui.button('No', on_click = dialog.close)
                        dialog.open()

                    def createVodList():
                        with vodDiv:
                            loadingVod.delete()
                            games = ui.list().props('bordered separator')

                            with games:
                                with ui.row():
                                    ui.item_label('Game').props('header').classes('text-bold')
                                    ui.space()
                                    ui.item_label('Icon').props('header').classes('text-bold')
                                    ui.space()
                                    ui.item_label('Champion').props('header').classes('text-bold')
                                    ui.space()
                                    ui.item_label('KDA').props('header').classes('text-bold')
                                    ui.space()
                                    ui.item_label('Gamemode').props('header').classes('text-bold')
                                    ui.space()
                                    ui.item_label('Actions').props('header').classes('text-bold')
                                ui.separator()
                            
                            vods = []

                            for file in os.listdir(VODPATH):
                                itemPath = os.path.join(VODPATH, file)
                                if os.path.isfile(itemPath):
                                    vods.append(file)
                            
                            # ensure all elements in the .csv file are only files that still exist in the VODs folder
                            existingFavVods = favVods.filter(pl.col('Name').is_in(vods))
                            existingFavVods = existingFavVods.sort('Name', descending = True)
                            print(f"existingFavVods = {existingFavVods['Name'].to_list()}")
                            with open(FAVSPATH, mode = 'w', encoding = 'utf8') as f:
                                existingFavVods.write_csv(f, include_header = True)
                            
                            vods.reverse() # vods goes by oldest to newest by default, reverse it

                            for file in vods:
                                # if file in events.values:
                                if file in pl.Series(events['Filename'].unique()).to_list():
                                    kills = len(events.filter(pl.col('Filename').is_in([file]) & pl.col('EventName').is_in(['ChampionKill'])))
                                    deaths = len(events.filter(pl.col('Filename').is_in([file]) & pl.col('EventName').is_in(['Death'])))
                                    assists = len(events.filter(pl.col('Filename').is_in([file]) & pl.col('EventName').is_in(['Assist'])))

                                    kda = f'{kills}/{deaths}/{assists}'

                                    champion = pl.Series(events.filter(pl.col('Filename').is_in([file])).select('Champion')).to_list()[0]
                                    if champion == 'MonkeyKing' or champion == 'Monkey King': champion = 'Wukong'

                                    gamemode = pl.Series(events.filter(pl.col('Filename').is_in([file])).select('Gamemode')).to_list()[0]
                                    
                                    # change gamemode names from how they're referred to in the API
                                    if gamemode == 'RUBY': gamemode = 'DOOMBOTS'
                                    elif gamemode == 'RUBY_TRIAL_1': gamemode = "VEIGAR'S CURSE"
                                    elif gamemode == 'RUBY_TRIAL_2': gamemode = "VEIGAR'S EVIL"
                                    elif gamemode == 'CLASSIC': gamemode = 'DRAFT'
                                    elif gamemode == 'CHERRY': gamemode = 'ARENA'

                                    with games:
                                        with ui.item().on_click(lambda e, file=file: handle_item_click_VODs(file)):
                                            with ui.item_section():
                                                ui.item_label(file)
                                            with ui.item_section():
                                                if champion == 'Wukong':
                                                    ui.image('/champIcons/MonkeyKing.png').classes('size-8')
                                                # remove spaces from champion names
                                                elif ' ' in champion:
                                                    champ = champion.replace(' ', '')
                                                    ui.image(f'/champIcons/{champ}.png').classes('size-8')
                                                # champions with apostrophes in their names should have them removed, and then capitalized
                                                elif "'" in champion:
                                                    champ = champion.replace("'", '').capitalize()
                                                    ui.image(f'/champIcons/{champ}.png').classes('size-8')
                                                else:
                                                    ui.image(f'/champIcons/{champion}.png').classes('size-8')
                                            with ui.item_section():
                                                ui.item_label(champion)
                                            with ui.item_section():
                                                ui.item_label(kda)
                                            with ui.item_section():
                                                ui.item_label(gamemode)
                                            with ui.item_section().props('side'):
                                                # if file not in favVods.values:
                                                with ui.row():
                                                    if file not in pl.Series(favVods['Name']).to_list():
                                                        ui.button(color = 'none', icon = 'star_border').on('click.stop', lambda e, file = file: (handle_button_click_VODS(e, file)))
                                                    else:
                                                        ui.button(color = 'none', icon = 'star').on('click.stop', lambda e, file = file: (handle_button_click_VODS(e, file)))
                                                    
                                                    ui.button(color = 'none', icon = 'delete').on('click.stop', lambda e, file = file: handle_del_button_VODS(file))
                                else:
                                    with games:
                                        with ui.item().on_click(lambda e, file=file: handle_item_click_VODs(file)):
                                            with ui.item_section():
                                                ui.item_label(file)
                                            with ui.item_section():
                                                ui.item_label('No events data')
                                            with ui.item_section():
                                                ui.item_label('-')
                                            with ui.item_section():
                                                ui.item_label('-')
                                            with ui.item_section():
                                                ui.item_label('-')
                                            with ui.item_section().props('side'):
                                                # if file not in favVods.values:
                                                with ui.row():
                                                    if file not in pl.Series(favVods['Name']).to_list():
                                                        ui.button(color = 'none', icon = 'star_border').on('click.stop', lambda e, file = file: (handle_button_click_VODS(e, file)))
                                                    else:
                                                        ui.button(color = 'none', icon = 'star').on('click.stop', lambda e, file = file: (handle_button_click_VODS(e, file)))
                                                    
                                                    ui.button(color = 'none', icon = 'delete').on('click.stop', lambda e, file = file: handle_del_button_VODS(file))
                    
                    if events.is_empty():
                        loadingVod.delete()
                        ui.label('No VODs found! Play a game first!').classes('self-center text-red-500 text-xl')
                    else: await run.io_bound(createVodList)

                with ui.tab_panel(clipsTab):
                    ui.label('Saved Clips').classes('font-bold text-2xl')

                    @ui.refreshable
                    def clipGrid():
                        with ui.element('div').classes('w-full') as clipDiv:
                            with ui.row() as clipPlaceholder:
                                ui.space()
                                ui.label('Generating clip thumbnails...')
                                ui.spinner(size='lg')
                                ui.space()

                        if os.path.exists('./data/thumbnails') and len(os.listdir('./data/thumbnails')) > 0:
                            app.add_media_files('/thumb', './data/thumbnails')

                            clips = [os.path.basename(file).split('.')[0] for file in os.listdir(CLIPPATH) if os.path.isfile(os.path.join(CLIPPATH, file))]
                            clips.reverse() # clips go by oldest to newest by default, reversing
                            
                            clipPlaceholder.delete()
                            with ui.grid(columns = 3).classes('w-full'):
                                for vid in clips:
                                    with ui.link(target = f'/watch/clip/{vid}').classes('no-underline'):
                                        with ui.card().tight():
                                            vidName = os.path.splitext(vid)[0]
                                            if os.path.exists(f'./data/thumbnails/{vidName}.webp'):
                                                ui.image(f'thumb/{vidName}.webp')
                                            else:
                                                ui.icon('error')
                                                ui.label('Failed to find thumbnail').classes('text-red-500')
                                            with ui.card_section():
                                                ui.label(vidName)

                    @background_tasks.await_on_shutdown
                    async def createThumbnails():
                        if not os.path.exists('./data/thumbnails'):
                            os.mkdir('./data/thumbnails')

                        itemPath = [os.path.join(CLIPPATH, file) for file in os.listdir(CLIPPATH) if os.path.isfile(os.path.join(CLIPPATH, file))]
                        thumbPath = [f'./data/thumbnails/{os.path.basename(file).split(".")[0]}.webp' for file in os.listdir(CLIPPATH) if os.path.isfile(os.path.join(CLIPPATH, file))]
                        command = [
                            ['./ffmpeg.exe', '-y', '-ss', '00:00:01', '-i', input, '-frames:v', '1', thumb, '-loglevel', 'error'] 
                            for input, thumb in zip(itemPath, thumbPath) if not os.path.exists(thumb)]
                        
                        async def thumbnailWorker(cmd, semaphore):
                            async with semaphore:
                                process = await asyncio.create_subprocess_exec(*cmd, creationflags = creationFlags)
                                await process.wait()
                        
                        sem = asyncio.Semaphore(os.cpu_count())

                        tasks = [thumbnailWorker(cmd, sem) for cmd in command]
                        
                        await asyncio.gather(*tasks)

                        clipGrid.refresh() # refresh clip grid to show new thumbnails
                        
                        # check if thumbnail has a corresponding clip in folder, if not, delete the thumbnail
                        clipList = [os.path.basename(file).split('.')[0] for file in os.listdir(CLIPPATH) if os.path.isfile(os.path.join(CLIPPATH, file))]
                        missingClipThumbs = [os.path.basename(file).split('.')[0] for file in os.listdir('./data/thumbnails') if os.path.basename(file).split('.')[0] not in clipList]

                        if len(missingClipThumbs) > 0:
                            for thumb in missingClipThumbs:
                                print(f"Removed {thumb}'s thumbnail, because its corresponding clip is missing.")
                                os.remove(os.path.join('./thumbnails', f'{thumb}.webp'))

                    clipGrid()
                    background_tasks.create(createThumbnails())

                with ui.tab_panel(settingsTab):
                    ui.label('Settings').classes('font-bold text-2xl')

                    with open(SETTINGSPATH, mode = 'r', encoding = 'utf8') as f:
                        settings = json.load(f)
                        maxVodSize = int(settings.get('vodFolderSizeLimit'))

                    def updateSettings(button):
                        settings.update({'vodFolderSizeLimit': int(maxVodSelect.value)})
                        with open(SETTINGSPATH, mode = 'w', encoding = 'utf8') as f:
                            json.dump(settings, f)
                        
                        ui.notify('Settings updated successfully!', type = 'positive')
                        button.disable()
                    
                    def compareSettings():
                        if maxVodSelect.value != maxVodSize: button.enable()
                        else: button.disable()
                    
                    ui.label('Maximum VOD Folder Size (GB):')
                    maxVodSelect = ui.number(value = maxVodSize, min = 3, max = 100, precision = 0, suffix = ' GB', on_change = lambda: compareSettings())
                    
                    button = ui.button('Save', on_click = lambda: updateSettings(button)).classes('justify-self-end')
                    button.disable()

@ui.page('/watch/vod/{fileName}')
async def watchVOD(fileName: str):
    with ui.splitter(horizontal = False, limits = (80, 90), value = 85, reverse = True).classes('w-full').props('before-class=overflow-hidden after-class=overflow-hidden') as splitter:
        with splitter.before:
            with ui.tabs().props('vertical').classes('w-full'):
                home = ui.tab('Home', icon='home')
                home.on('click', lambda: ui.navigate.to('/'))
        with splitter.after:
            path = f'/vods/{fileName}'
            events = pl.read_csv(EVENTPATH)
            
            command = ['./ffprobe.exe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', f'{VODPATH}/{fileName}']
            duration = subprocess.check_output(command, creationflags = creationFlags).decode('utf-8').strip()
            duration = math.floor(float(duration))

            if fileName in pl.Series(events['Filename'].unique()).to_list():
                with ui.row().classes('w-full flex-col mx-3 2xl:flex-row'):
                    v = ui.video(path).classes('w-full 2xl:grow-7 2xl:w-[50%]').props('autoplay controls')

                    rows = events.filter(pl.col('Filename').is_in([fileName])).select(['EventName', 'EventTime'])

                    def handle_row_click(event):
                        clicked_row_data = event.args[1]

                        time = clicked_row_data['EventTime']

                        sec = time.split(':') # time is in min:sec format, convert back to seconds
                        sec = [float(item) for item in sec]

                        sec[0] = sec[0] * 60 # convert min to sec
                        sec[0] += sec[1] # add sec to previously converted min
                        v.seek(sec[0])
                        v.play()
                    
                    with ui.column().classes('w-full 2xl:shrink 2xl:max-w-lg'):
                        filterSelect = ui.select(label = 'Filter Events Table', options = ['ChampionKill', 'Multikill', 'Assist', 'Death', 'Ace', 'Custom'], 
                                            value = ['ChampionKill', 'Multikill', 'Assist', 'Death', 'Ace', 'Custom'], multiple = True).classes('self-center 2xl:self-auto 2xl:max-w-md').props('use-chips')
                    
                        table = ui.table.from_polars(rows, pagination=5).classes('self-center shrink mb-3 2xl:mb-0 2xl:self-auto 2xl:max-w-md 2xl:max-h-sm')
                        table.on('rowClick', handle_row_click)

                        def applyEventFilter():
                            selectedEvents = filterSelect.value

                            rows = events.filter(pl.col('Filename').is_in([fileName]))

                            if set(selectedEvents) == set(['ChampionKill', 'Multikill', 'Assist', 'Death', 'Ace', 'Custom']):
                                table.rows = rows.to_dicts()
                                table.update()
                            elif selectedEvents == []:
                                table.rows = []
                                table.update()
                            else:
                                table.rows = rows.filter(pl.col(['EventName']).is_in(selectedEvents)).to_dicts()
                                table.update()
                        
                        filterSelect.on_value_change(applyEventFilter)
            else:
                v = ui.video(path).classes('mx-3 w-full')
            
            async def rangeMinMax(event):
                global minVal, maxVal
                minVal = event.value['min']
                maxVal = event.value['max']

                v.seek(minVal)
            
            @background_tasks.await_on_shutdown
            async def clipVideo(notif):
                notif.message = 'Clipping video...'
                notif.spinner = True
                
                now = datetime.datetime.now()
                clipFileName = f'clip_{now.strftime("%Y-%m-%d %H-%M-%S")}.mp4'

                command = ['./ffmpeg.exe', '-y', '-hide_banner', '-loglevel', 'error', '-stats', 
                           '-ss', str(minVal), '-to', str(maxVal), 
                           '-i', str(os.path.join(VODPATH, fileName)),
                            str(os.path.join(CLIPPATH, clipFileName))]
                
                process = await asyncio.create_subprocess_exec(*command, stderr = asyncio.subprocess.PIPE, creationflags = creationFlags)
                
                while True:
                    try:
                        line = await process.stderr.readuntil(b'\r')
                        lineDecoded = line.decode('utf-8')

                        if 'time=' in lineDecoded:
                            currentSeconds = lineDecoded.split('time=')[1].split(' ')[0].split(':')[-1]

                            if currentSeconds == 'N/A': continue
                            else:
                                progress = (float(currentSeconds) / (maxVal - minVal)) * 100

                                notif.message = f'Clipping video... {round(progress)}%'
                        else: continue
                        if not line: break
                    except asyncio.IncompleteReadError: break

                await process.wait()
                
                app.add_media_file(local_file = f'{CLIPPATH}/{clipFileName}', url_path = f'/clips/{clipFileName}', )

                await asyncio.sleep(2)
                
                return clipFileName
            
            async def startClip():
                notif = ui.notification(timeout = None)

                clipFileName = await background_tasks.create(clipVideo(notif))

                notif.dismiss()

                with ui.dialog(value = True) as dialog, ui.card():
                    ui.label('Clip created successfully! Would you like to view it now?')
                    with ui.row().classes('self-center'):
                        ui.button('Yes', on_click = lambda: ui.navigate.to(f'/watch/clip/{clipFileName.split(".")[0]}'))
                        ui.space()
                        ui.button('No', on_click = dialog.close)
                        ui.space()
                        ui.button('Open Clip in Explorer', on_click= lambda: subprocess.run(['explorer', '/select,', os.path.abspath(os.path.join(CLIPPATH, clipFileName))], check=True)) 
            
            with ui.expansion('Clip!', icon='movie_creation', value = True). classes('mx-3 w-full'):
                with ui.row().classes('w-full'):
                    ui.space()
                    ui.button('Clip', on_click = startClip)

                clipRange = ui.range(min = 0, max = duration, value = {'min' : 0, 'max': 20}, on_change = rangeMinMax).props('label-always').classes('w-full')
                
                ui.label().bind_text_from(clipRange, 'value', 
                                        backward = lambda minConvert: f'{int(math.floor(minConvert["min"]) / 60):02d}:{(minConvert["min"] % 60):02d} to {int(math.floor(minConvert["max"]) / 60):02d}:{(minConvert["max"] % 60):02d}').classes('text-lg self-center')

            
            if fileName not in pl.Series(events['Filename'].unique()).to_list():
                ui.label('No events data found for this VOD.').classes('self-center text-red-500 text-xl')


@ui.page('/watch/clip/{fileName}')
async def watchClip(fileName: str):
    with ui.splitter(horizontal = False, limits = (80, 90), value = 85, reverse = True).classes('w-full').props('before-class=overflow-hidden after-class=overflow-hidden') as splitter:
        with splitter.before:
            with ui.tabs().props('vertical').classes('w-full'):
                home = ui.tab('Home', icon='home')
                home.on('click', lambda: ui.navigate.to('/'))
        with splitter.after:
            path = f'/clips/{fileName}.mp4'
            ui.video(path).classes('mx-3 w-full')

            def highlightVideo():
                absolutePath = f'{os.path.abspath(os.path.join(CLIPPATH, fileName))}.mp4'
                print(absolutePath)

                if os.path.exists(absolutePath):
                    subprocess.run(['explorer', '/select,', absolutePath], check=True) # ignore if it returns exit status 1
                else:
                    print('File not found')
            
            with ui.row().classes('w-full'):
                ui.space()
                ui.button('Open Clip in Explorer', on_click=highlightVideo)
                ui.space()

if __name__ == '__main__':
    freeze_support()
    ui.run(title='LiveClient GUI', reload=False, native=True, window_size=(1600, 950), dark = True, favicon='favicon.ico')