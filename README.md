# League LiveClient Markers
League LiveClient Markers.py is meant for use with [OBS Advanced Scene Switcher](https://obsproject.com/forum/resources/advanced-scene-switcher.395/) (and [OBS Websocket](https://github.com/obsproject/obs-websocket)) so that it automatically runs when conditions are met!

This script connects to OBS Websocket to get the status and output path of the active recording, and Riot's [Live Client API](https://developer.riotgames.com/docs/lol#game-client-api_live-client-data-api) to get the player's username, chosen champion, and events that occur throughout the game. Once League of Legends is closed, events are filtered to find ones that only include you, and are then saved to a .csv file!

This project also has a GUI made with [NiceGUI](https://nicegui.io/)! Through the GUI, you can watch all of your recordings and clips, view events associated to those recordings if any, and clip them.

Note: This program has only been tested on Windows 10 and 11 x64 systems! It most likely doesn't work on other platforms.

---

## Installation

### Using the Installer

The installer includes all of the required files & folder structure (ffmpeg, and portable OBS with Advanced Scene Switcher already installed & ready to detect if League of Legends is open). Having OBS open on startup isn't required, but it is convenient!

After installing, make sure to open OBS > go to Tools > WebSocket Server Settings > Enable WebSocket Server, and allow OBS through only private network firewalls *(not public)*! If the Windows Security Alert doesn't pop up after clicking apply and OK, you might have to close and reopen OBS.

OBS Websocket is required for LiveClient to function. Advanced Scene Switcher is already set up with the required actions, but please test it in Practice Tool with a bot first (try killing it a couple of times)! If the GUI pops up a little after you leave the game and the VOD shows up in the list, the app is working correctly.

Lastly, OBS portable is set up to minimize to tray! Try to minimize it instead of closing it, or LiveClient won't record your games automatically!

### Using the Scripts Directly

If you choose not to use the installer, the scripts requires the following folder structure:

Parent folder *(can be any folder you like, I prefer Videos)* > LiveClient > ddragon.

League_LiveClient_Markers.py depends on a portable version of OBS, but if you don't want to use that, remove the `with open` at the top of the script and hardcode your WebSocket host & password. 

The Python scripts should all be in the LiveClient folder. Make sure to install each module imported in the scripts, and create the following subfolders under LiveClient: \clips, \vods, and \data. The LiveClient scripts will create them if they don't already exist, but OBS needs to be set to save your recordings in \vods.

The following is the Advanced Scene Switcher Macro used for the installer version (but make sure to change the `${LiveClientPath}` variable to where you have the scripts saved):

<details>

<summary>Advanced Scene Switcher Macro</summary>

`AAAROXiczVZtT+M4EP4rOev6rSmU0u5R3Re25e6Q6MJty55Wqwq5ySSx6tqR7aRUVf/7jeO0SZbeglacQAIUxvPmZ+aZ8ZasaKCkJsNvWyLoCsiQXGZGep8hkCr0boDGGZA2iZXMUjKMKNfQJinNNExpDh8hoTmTigxPS2lNR1HOgR8EQQLBciRFyAyTQl+Lu+81aGBPZorFMaiJDNFZt030kqVXjxDciqmhyhy0tZHpZeB8RZ+kGUtRRbf5JVKZEVNBxsxVTnlGrW5dY5Shj9UhpZFN8FoYUKhdpf1DpS2xnqH2cdrptYnZpPZzh2EEMwU6OShdxO+iNJTBcgrGMBFra6sgZhp91i5HRUg5XmmMqmRoVAbO7B8mQrnGOhUHbZJQ/TkTHzNjrHOnh7I7W4wnUkTQZPqGLmqoJyxOOP6a66iqzkxlFZhq738Gj3gZgvFIWe6GvIhJ7J2fnt07GZ4GjSAuo1Kpiu9RBZ5Nu9Ow+MMm9COTImNrY6G6DlGBhrnWftHmvhX6UUgX0Vmv558NLn7zzwf9M/8C+pE/6J0PaDSAsLuwaTbqVZi7ZjsEnKacGazZndTMdRZyKLVc+jDYtcvPQb+/m5f2V5ia8/Hfpufn5wfb7ocLa7vvjb+kWcJGN0nohGg/P8BeFxkZxxzuvhdXgBaRNcQrEKbekIHknKYawqd8aXZPUJeRycbjxWebgKALbu1d8zXgZLYwqZIBaI2qXMYsKEgSZqpgKZKfRczyYUsMW8EDZqyNokw4MmmwV9DH+NfvnD7HPxTvgw+JG3GejHDYxYBOO/Bo6x9JvFpFATx7xNJHLLax3OXqs84wOw7cXWVaYmsTqMWd70fcW8KuAxDwoNfMBAnZJ1QgFFCRUwvJBHHGIxw08FhDtlvHtXAzBQ6l/XZ/1t7vkSfAlksF70r2wWoOXFT0jGUWjhazvcdKZBmfGVJ1yvER/GwLtMmC4zC4F4bx2cF7Y4UUN5ztvfxkuVwVmtX63femuLu0t+A0WHo6UADCi5RceQtA1x4TnknAUzW4ni3rmrLnYOm+gBqVh7OfRtamcihd/eTNWn5jZ8fmQUiDUyVwAOFQxgFA41qrHgD3cFV62r42IPwFNQ0zvHgahTkVAYTe1PaGNy1IhFMK4wRFb/66vWE5jDjDS95Rk+wifB7hUQf/kPcBRr2r9uTv2nHHQztvyWh4cq/R6mQtecRPvrAQpC7moVpRu3Fbo9HXr35rMvFb47HXShK/tVr5rWKSBwlNcVV9chOAvCpt7HvTezpUIEfv2sM3ayfQ+YsQcM8XtwGqmZ5ivY6V0IV8qKQPE6qW6LVcFGuplnizMUNkjVSbYz4s1spe/tt89wxJX8qwA3bNBQOHR8ZbLpljTXb63prszeaKTNN3N1eOMW6M29kg2WzRvLyokbdOcFfRhUQu9k/jhcfZqlg8r806F/uWh6433h/XXhPo2xRB/fP++v+YXod/3x+Ec/vGTDPzhSpmb+0mVl7+V/K7mRrZza1Z3rAQRzXxBYcb47JacWXKpNM5cT/2vQQRzThm4I5I9Ub/O4Os8D+v5Uy6nV6v0yW7fwG7mvLH`

</details>

The GUI requires [ffmpeg and ffprobe](https://www.gyan.dev/ffmpeg/builds/) to be in the LiveClient folder.