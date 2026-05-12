# League LiveClient Markers
League LiveClient Markers.py is meant for use with [OBS Advanced Scene Switcher](https://obsproject.com/forum/resources/advanced-scene-switcher.395/) (and [OBS Websocket](https://github.com/obsproject/obs-websocket)) so that it automatically runs when conditions are met!

This script connects to OBS Websocket to get the status and output path of the active recording, and Riot's [Live Client API](https://developer.riotgames.com/docs/lol#game-client-api_live-client-data-api) to get the player's username, chosen champion, and events that occur throughout the game. Once League of Legends is closed, events are filtered to find ones that only include you*, and are then saved to a .csv file!

> [!IMPORTANT]
> There are some hardcoded variables (like relative paths, and username in the case that `getPlayerInfo()` fails after 5 tries). Change them if needed!
>
> The script requires the following folder structure:
>
> Parent folder (can be anywhere) > LiveClient (can be named anything). The Python scripts should all be in this folder. You need to have an .env file in this folder containing `OBS_WEBSOCKET=(your OBS Websocket password here)` for authentication, otherwise, the script won't work!
>
> The GUI also requires having the FFmpeg .exes in the LiveClient folder.
>
> The LiveClient script will create the following subfolders if they don't already exist: clips, vods, and data (for saving events, and logging).

This project also has a GUI made with [NiceGUI](https://nicegui.io/)! Through the GUI, you can view all VODs and clips in their respective folders, view events associated to those VODs if any, and clip them. Note: It was only tested on Windows.