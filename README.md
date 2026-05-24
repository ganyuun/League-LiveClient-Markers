# League LiveClient Markers
League LiveClient Markers.py is meant for use with [OBS Advanced Scene Switcher](https://obsproject.com/forum/resources/advanced-scene-switcher.395/) (and [OBS Websocket](https://github.com/obsproject/obs-websocket)) so that it automatically runs when conditions are met!

This script connects to OBS Websocket to get the status and output path of the active recording, and Riot's [Live Client API](https://developer.riotgames.com/docs/lol#game-client-api_live-client-data-api) to get the player's username, chosen champion, and events that occur throughout the game. Once League of Legends is closed, events are filtered to find ones that only include you, and are then saved to a .csv file!

There's also a custom hotkey (CTRL + F1) to save a custom marker during a League game.

This project also has a GUI made with [NiceGUI](https://nicegui.io/)! Through the GUI, you can watch all of your recordings and clips, view events associated to those recordings if any, and clip them.

> [!WARNING]
> This program has only been tested on Windows 10 and 11 x64 systems! It doesn't work on other platforms.

---

## Installation

### Using the Installer

1. Download and run the latest installer in the [Releases tab](https://github.com/ganyuun/League-LiveClient-Markers/releases)

2. If preferred, have OBS Portable open on startup to make sure your games are recorded

3. Enable OBS Websocket (required for LiveClient to function!)

After installing, open OBS > go to Tools > WebSocket Server Settings > Enable WebSocket Server, and allow OBS through only private network firewalls *(not public)*! If the Windows Security Alert doesn't pop up after clicking apply and OK, you might have to close and reopen OBS.

Lastly, OBS portable is set up to minimize to tray! Try to minimize it instead of closing it, or LiveClient won't record your games automatically!

### Using the Scripts Directly

1. Use the pyproject.toml file to ensure you have all dependencies & the required Python version installed!

2. Create the following folder structure:

- /LiveClient *(all of the scripts should be in here, along with the [ffmpeg and ffprobe](https://www.gyan.dev/ffmpeg/builds/) .exe's)*
  - /ddragon (and download the images from this repository's ddragon folder)
  - /vods
  - /clips
  - /data/logs
  - /[obs](https://obsproject.com/kb/portable-mode) (with [Advanced Scene Switcher installed](https://obsproject.com/forum/resources/advanced-scene-switcher.395/)) **(optional)**

2. Download [OBS portable](https://obsproject.com/kb/portable-mode), and install [Advanced Scene Switcher](https://obsproject.com/forum/resources/advanced-scene-switcher.395/) **(optional)**

Make sure to download the .zip file (ex. `advanced-scene-switcher-1.33.1-windows-x64.zip`) and copy the files/folders to the matching directories in OBS Portable.

> [!IMPORTANT]
> If you already have OBS installed and don't want to use OBS Portable, install [Advanced Scene Switcher](https://obsproject.com/forum/resources/advanced-scene-switcher.395/) using the .exe, and enter your OBS Websocket host and password in the LiveClient GUI's settings.

3. Set up OBS

    1. Set OBS to output in `/LiveClient/vods`
    2. Add a [Game Capture](https://obsproject.com/kb/game-capture-setup-guide) source for League of Legends
    3. Enable OBS WebSocket by going to Tools > WebSocket Server Settings
    4. Set up the Advanced Scene Switcher macro

> [!TIP]
> If you already have OBS installed, you may want to create a [new profile](https://obsproject.com/kb/profiles) for LiveClient.

The following is the Advanced Scene Switcher Macro used for the installer version. Make sure to change each "run" step to `cmd`, then add the argument `py {name of script}.py`.

If you're not using OBS Portable, make sure to set the `${LiveClientPath}` variable to the LiveClient folder (or where you have the scripts saved). The working directory must be the same LiveClient folder:

<details>
<summary>Advanced Scene Switcher Macro</summary>

`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`

</details>

Before trying out LiveClient in real games, make sure it works first by testing it in Practice Tool and killing a bot a couple times to save events! If the GUI pops up a little after you leave the game and the VOD shows up in the list, the app is working correctly.