# League LiveClient Markers
This Python script is meant for use with [OBS Advanced Scene Switcher](https://obsproject.com/forum/resources/advanced-scene-switcher.395/) (and [OBS Websocket](https://github.com/obsproject/obs-websocket)) so that it automatically runs when conditions are met!

This script connects to OBS Websocket to get the status and output path of the active recording, and Riot's [Live Client API](https://developer.riotgames.com/docs/lol#game-client-api_live-client-data-api) to get the player's username, chosen champion, and events that occur throughout the game. Once League of Legends is closed, events are filtered to find ones that only include you*, and are then saved to a .csv file!

> [!IMPORTANT]
> There are some hardcoded variables (like paths, and username in the case that `getPlayerInfo()` fails after 5 tries). Change them if needed!