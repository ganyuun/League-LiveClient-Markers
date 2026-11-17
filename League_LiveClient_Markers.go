package main

import (
	"bytes"
	"context"
	"crypto/tls"
	"database/sql"
	"encoding/csv"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"log"
	"math"
	"net/http"
	"os"
	"slices"
	"strconv"
	"strings"
	"time"

	_ "modernc.org/sqlite"

	"github.com/andreykaipov/goobs"
	"github.com/andreykaipov/goobs/api/events"
	"github.com/zalando/go-keyring"
)

const ALLDATA string = "https://127.0.0.1:2999/liveclientdata/allgamedata"
const EVENTDATA string = "https://127.0.0.1:2999/liveclientdata/eventdata"
const VODPATH = "./vods/"
const EVENTPATH = "./data/events.csv"
const DBPATH = "./data/data.db"
const SETTINGSPATH = "./data/settings.json"
const CLIPPATH = "./clips/"
const FAVSPATH = "data/favoritedVODs.csv"

var LOGPATH string = fmt.Sprintf("./data/logs/log %s.txt", time.Now().Format("01-02-2006"))

func Exists(path string) (bool, error) {
	_, err := os.Stat(path)
	if err == nil {
		return true, nil
	}
	if errors.Is(err, fs.ErrNotExist) {
		return false, nil
	}
	return false, err
}

func main() {
	logFile, err := os.OpenFile(LOGPATH, os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0644)

	if err != nil {
		panic(err)
	}

	logWriter := io.MultiWriter(os.Stdout, logFile)
	log.SetOutput(logWriter)

	if migrationNeeded, err := MigrateSQLite(); err == nil {
		if migrationNeeded == true {
			fmt.Println("Migration successful")
		}
	} else {
		panic(err)
	}

	port, password, err := obsWebsocketCredentials()

	if err != nil {
		log.Fatalln(err)
	}

	obsClient, err := goobs.New(fmt.Sprintf("localhost:%d", port), goobs.WithPassword(password))
	defer obsClient.Disconnect()

	if err != nil {
		log.Fatalln(err)
	}

	status, err := obsClient.Record.GetRecordStatus()

	log.Printf("Is OBS currently recording? %v", status.OutputActive)

	if status.OutputActive {
		outputCh := make(chan string)
		outputStopped := make(chan bool)

		go obsListener(obsClient, outputCh, outputStopped)

		tr := &http.Transport{TLSClientConfig: &tls.Config{InsecureSkipVerify: true}}
		client := &http.Client{Transport: tr}

		if username, champ, mode, delayBool, err := getPlayerInfo(client); err == nil {
			var delay float64 = 0

			if delayBool {
				status, err = obsClient.Record.GetRecordStatus()
				delay = (status.OutputDuration / 1000) + 2 // outputDuration is in milliseconds, convert to sec
				log.Printf("Accounted for delay in recording due to the loading screen. It is currently %.3f seconds into the recording!", delay)
			}

			events := getEvents(client, outputStopped)
			filteredEvents := filterEvents(username, events, delay)
			err = writeToFile(outputCh, champ, mode, filteredEvents, client)

			if err != nil {
				log.Fatalf("Encountered an error in writeToFile! Error: %s", err)
			}

			log.Println("main: Wrote events to file successfully!")
		}
	}
}

func obsWebsocketCredentials() (port int, password string, err error) {
	p, errP := keyring.Get("LiveClient", "port")
	pass, errPass := keyring.Get("LiveClient", "websocketPassword")

	if errP != nil || errPass != nil {
		log.Println("WARNING: OBS credentials not found in keyring!")

		if result, err := Exists("./obs/config/obs-studio/plugin_config/obs-websocket"); result == true && err == nil {
			type response struct {
				Password string `json:"server_password"`
				Port     int    `json:"server_port"`
			}

			f, err := os.ReadFile("./obs/config/obs-studio/plugin_config/obs-websocket/config.json")

			if err != nil {
				return 0, "", err
			}

			var config response
			json.Unmarshal(f, &config)

			err = keyring.Set("LiveClient", "port", strconv.Itoa(config.Port))

			if err != nil {
				return 0, "", err
			}

			err = keyring.Set("LiveClient", "websocketPassword", config.Password)

			if err != nil {
				return 0, "", err
			}

			return config.Port, config.Password, nil
		} else {
			return 0, "", errors.New("Unable to find OBS Websocket credentials in keyring or JSON file! Did you set up Websocket in OBS Portable?")
		}
	}

	portInt, err := strconv.Atoi(p)

	if err != nil {
		panic(err)
	}

	return portInt, pass, nil
}

func obsListener(client *goobs.Client, output chan string, outputStopped chan bool) {
	client.Listen(func(event any) {
		switch e := event.(type) {
		case *events.RecordStateChanged:
			if e.OutputState == "OBS_WEBSOCKET_OUTPUT_STOPPED" {
				if _, vodName, found := strings.CutLast(e.OutputPath, "/"); found == true {
					log.Printf("obsListener: Recording stopped! Output state is %v and outputPath is %s\n", e.OutputState, vodName)
					output <- vodName
				} else {
					log.Printf("obsListener: Recording stopped! Output state is %v and outputPath is %s\n", e.OutputState, vodName)
					_, vodName, _ := strings.CutLast(e.OutputPath, "\\")
					output <- vodName
				}

				outputStopped <- true
			}
		}
	})
}

func getPlayerInfo(client *http.Client) (riotName, champion, gamemode string, delay bool, err error) {
	type playerInfo struct {
		ActivePlayer struct {
			RiotName string `json:"riotIdGameName"`
			Tagline  string `json:"riotIdTagLine"`
		} `json:"ActivePlayer"`
		AllPlayers []struct {
			Champion string `json:"championName"`
			RiotName string `json:"riotIdGameName"`
		} `json:"allPlayers"`
		GameData struct {
			Gamemode string `json:"gameMode"`
		} `json:"gameData"`
	}

	type eventOverview struct {
		EventList []struct {
			ID int `json:"EventID"`
		} `json:"Events"`
	}

	var info playerInfo
	resp, err := client.Get(ALLDATA)

	if err != nil {
		log.Println("getPlayerInfo: Failed to get JSON data from ALLDATA endpoint! Trying again in 10 sec...")

		for i := range 5 {
			time.Sleep(10 * time.Second)

			resp, err := client.Get(ALLDATA)

			if err == nil {
				err = json.NewDecoder(resp.Body).Decode(&info)
				resp.Body.Close()
				break
			}

			resp.Body.Close()

			if i == 5 {
				log.Fatal("getPlayerInfo: League client not open! Quitting...")
			}
		}
	}

	if resp.StatusCode == http.StatusOK {
		defer resp.Body.Close()

		err = json.NewDecoder(resp.Body).Decode(&info)

		// if the length of the allPlayers property is 0, then the rest of the function can't run properly
		// block script until it can get the user's username/tagline/other ingame stuff successfully, or use saved username as fallback
		if len(info.AllPlayers) > 0 {
			log.Printf("getPlayerInfo: Got the player's information! %s, %s, %s, %s\n", info.ActivePlayer.RiotName, info.ActivePlayer.Tagline, info.AllPlayers[0].RiotName, info.GameData.Gamemode)
		} else {
			for i := range 6 {
				if i == 5 {
					exists, err := Exists(SETTINGSPATH)

					if err != nil {
						return "", "", "", false, errors.New("Failed to get the player's information 5 times, and failed to fallback on player's saved username.")
					}

					if exists {
						type settingsFile struct {
							Username string `json:"username"`
						}

						var settings settingsFile

						f, err := os.ReadFile(SETTINGSPATH)

						if err != nil {
							return "", "", "", false, errors.New("Failed to get the player's information 5 times, and failed to read settings to fallback on player's saved username.")
						}

						err = json.Unmarshal(f, &settings)

						if err != nil {
							return "", "", "", false, errors.New("Failed to get the player's information 5 times, and failed to unmarshal settings to fallback on player's saved username.")
						}

						return settings.Username, "", "", false, nil
					}
				}

				time.Sleep(1 * time.Second)

				resp, err := client.Get(ALLDATA)
				resp.Body.Close()

				if err != nil {
					fmt.Println("getPlayerInfo: Failed to get JSON data from ALLDATA endpoint while running in for loop!")
					panic(err)
				}

				if resp.StatusCode == http.StatusOK {
					err = json.NewDecoder(resp.Body).Decode(&info)

					if err != nil {
						fmt.Println("getPlayerInfo: Failed to decode JSON from ALLDATA endpoint!")
						panic(err)
					}

					if len(info.AllPlayers) > 0 {
						fmt.Println("getPlayerInfo: Got the player's information!", info.ActivePlayer.RiotName, info.ActivePlayer.Tagline, info.AllPlayers[0].RiotName, info.GameData.Gamemode)
						break
					}
				}
			}
		}

		if err != nil {
			fmt.Println("getPlayerInfo: Failed to decode JSON from ALLDATA endpoint!")
			panic(err)
		}
	}

	// check if activePlayer name matches what's saved in settings
	if exist, err := Exists(SETTINGSPATH); exist && err == nil {
		var settings map[string]any

		f, err := os.ReadFile(SETTINGSPATH)

		if err != nil {
			log.Fatal("getPlayerInfo: Failed to open settings file!")
		}

		err = json.Unmarshal(f, &settings)

		if err != nil {
			log.Fatal("getPlayerInfo: Failed to unmarshal settings file!")
		}

		if settings["username"] != info.ActivePlayer.RiotName || settings["tagline"] != info.ActivePlayer.Tagline {
			settings["username"] = info.ActivePlayer.RiotName
			settings["tagline"] = info.ActivePlayer.Tagline
			settingsJSON, err := json.Marshal(settings)

			if err != nil {
				log.Fatal("getPlayerInfo: Failed to marshal settings!")
			}

			os.WriteFile(SETTINGSPATH, settingsJSON, 0666)
		}
	} else {
		var settings = map[string]any{"username": info.ActivePlayer.RiotName, "tagline": info.ActivePlayer.Tagline, "vodFolderSizeLimit": 50}
		settingsJSON, err := json.Marshal(settings)

		if err != nil {
			log.Fatal("getPlayerInfo: Failed to marshal new settings file!")
		}

		os.WriteFile(SETTINGSPATH, settingsJSON, 0666)
	}

	var overview eventOverview
	resp, err = client.Get(EVENTDATA)

	if err != nil {
		log.Fatal("getPlayerInfo: Failed to get JSON data from EVENTDATA endpoint!")
	}

	err = json.NewDecoder(resp.Body).Decode(&overview)

	if err != nil {
		log.Fatal("getPlayerInfo: Failed to decode JSON from EVENTDATA endpoint!")
	}

	// the loading screen is most likely included in the recording, which will cause a delay
	// if there are 2+ events already available in the API (one of them should be GameStart), it's most likely that we're rejoining a game, so don't account for any delay
	log.Printf("getPlayerInfo: There are currently %d event(s) in the API!", len(overview.EventList))

	if len(overview.EventList) <= 2 {
		return info.ActivePlayer.RiotName, info.AllPlayers[0].Champion, info.GameData.Gamemode, true, nil
	} else {
		return info.ActivePlayer.RiotName, info.AllPlayers[0].Champion, info.GameData.Gamemode, false, nil
	}
}

// events structure from game API
// EventNames to pay attention to: GameStart, MinionsSpawning, FirstBlood, ChampionKill, Multikill, Ace, GameEnd
type gameEvents struct {
	ID        int      `json:"EventID"`    // present for all events
	Name      string   `json:"EventName"`  // present for all events
	Time      float64  `json:"EventTime"`  // present for all events
	Killer    string   `json:"KillerName"` // only present for ChampionKill, MultiKill
	Victim    string   `json:"VictimName"` // only present for ChampionKill, MultiKill
	Assisters []string `json:"Assisters"`  // only present for ChampionKill
	Acer      string   `json:"Acer"`       // only present for Ace
	Recipient string   `json:"Recipient"`  // only present for FirstBlood
}

type leagueEvents []gameEvents

func getEvents(client *http.Client, outputStopped chan bool) leagueEvents {
	log.Println("getEvents: Started saving events!")

	var wrapper struct {
		Events []gameEvents `json:"Events"`
	}

	var events leagueEvents

	for {
		resp, err := client.Get(EVENTDATA)

		if err != nil {
			log.Println("getEvents: Failed to get JSON from EVENTDATA endpoint! Is the game closed?", err) // error might occur when game closes

			if len(events) > 0 {
				return events
			}

			return make(leagueEvents, 0)
		}

		if resp.StatusCode == http.StatusOK {
			err = json.NewDecoder(resp.Body).Decode(&wrapper)

			if err != nil {
				log.Println("getEvents: Failed to decode JSON from EVENTDATA endpoint! Is the game closed?", err)

				return events
			}

			events = wrapper.Events

			select {
			case val, ok := <-outputStopped:
				if val && ok {
					log.Println("getEvents: OBS recording stopped! Ending getEvents loop.")
					return events
				}
			default:
				continue
			}

			resp.Body.Close()
			time.Sleep(1 * time.Second)
		}
	}
}

type conditionedEvent struct {
	Name string
	Time string
}

func filterEvents(username string, events leagueEvents, delay float64) []conditionedEvent {
	var filteredEvents []conditionedEvent

	for _, e := range events {
		// convert seconds float -> MM:SS string
		timeDelay := e.Time + delay
		min := math.Floor(timeDelay / 60)
		sec := math.Mod(timeDelay, 60)
		timeFormat := fmt.Sprintf("%02.0f:%06.3f", min, sec)

		switch e.Name {
		case "FirstBlood":
			if e.Recipient == username {
				filteredEvents = append(filteredEvents, conditionedEvent{Name: "FirstBlood", Time: timeFormat})
			}
		case "ChampionKill":
			if e.Killer == username {
				filteredEvents = append(filteredEvents, conditionedEvent{Name: "ChampionKill", Time: timeFormat})
			} else if e.Victim == username {
				filteredEvents = append(filteredEvents, conditionedEvent{Name: "Death", Time: timeFormat})
			} else if slices.Contains(e.Assisters, username) {
				filteredEvents = append(filteredEvents, conditionedEvent{Name: "Assist", Time: timeFormat})
			}
		case "Multikill":
			if e.Killer == username {
				filteredEvents = append(filteredEvents, conditionedEvent{Name: "Multikill", Time: timeFormat})
			}
		case "Ace":
			filteredEvents = append(filteredEvents, conditionedEvent{Name: "Ace", Time: timeFormat})
		}
	}

	return filteredEvents
}

func writeToFile(filenameCh chan string, champ string, mode string, events []conditionedEvent, client *http.Client) error {
	filename := <-filenameCh

	result, err := Exists(DBPATH)

	if err != nil {
		log.Println("writeToFile: Encountered error while checking if SQLite3 database exists; defaulting to .csv output.", err)
	}

	// writing to database if it exists
	if result {
		db, err := sql.Open("sqlite", fmt.Sprintf("file:%s?_pragma=foreign_keys(1)", DBPATH))

		if err != nil {
			fmt.Println("writeToFile: Encountered error opening SQLite3 database!", err)
			return err
		}

		// remains blank if getMatchResult() fails, or becomes "WIN" / "LOSS"
		var result string = ""

		if !slices.Contains([]string{"PRACTICETOOL", "JADE", "KIWI"}, mode) {
			result, err = getGameResult(client)

			if err != nil {
				log.Println("writeToFile: Calling getGameResult() failed:", err)
			}
		}

		if len(events) > 0 {
			killCount := len(Filter(events, func(e conditionedEvent) bool {
				return e.Name == "ChampionKill"
			}))

			deathCount := len(Filter(events, func(e conditionedEvent) bool {
				return e.Name == "Death"
			}))

			assistCount := len(Filter(events, func(e conditionedEvent) bool {
				return e.Name == "Assist"
			}))

			db.Exec(`
				INSERT INTO videos (Filename, Champion, KDA, Gamemode, Result)
				VALUES (?, ?, ?, ?, ?)`,
				filename, champ, fmt.Sprintf("%d/%d/%d", killCount, deathCount, assistCount), mode, result)

			ctx := context.Background()
			eventTx, err := db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelReadCommitted})

			if err != nil {
				log.Fatalln("writeToFile: Failed to create SQLite3 transaction to write events!", err)
			}

			for _, e := range events {
				_, err = eventTx.ExecContext(
					ctx,
					`INSERT INTO events (Filename, EventName, EventTime) 
					VALUES (?, ?, ?)`,
					filename, e.Name, e.Time)

				if err != nil {
					eventTx.Rollback()
					log.Fatalln("writeToFile: Encountered an error while writing events transaction.", err)
				}
			}

			err = eventTx.Commit()

			if err != nil {
				eventTx.Rollback()
				log.Fatalln("writeToFile: Encountered an error while committing events transaction.", err)
			}
		} else {
			db.Exec(`
				INSERT INTO videos (Filename, Champion, KDA, Gamemode, Result)
				VALUES (?, ?, ?, ?, ?)`,
				filename, champ, "0/0/0", mode, result)
		}

		db.Close()
		return nil
	}

	// appending to .csv if it already exists
	exists, err := Exists(EVENTPATH)

	if err != nil {
		log.Fatalln("writeToFile: Encountered an error while checking if events.csv exists!", err)
	}

	if exists {
		f, err := os.OpenFile(EVENTPATH, os.O_APPEND, 0644)

		if err != nil {
			log.Fatalln("writeToFile: Encountered an error while trying to read events.csv:", err)
		}

		defer f.Close()

		writer := csv.NewWriter(f)

		for _, e := range events {
			writer.Write([]string{filename, champ, e.Name, e.Time, mode})
		}

		writer.Flush()

		return nil
	}

	// if the user doesn't have a sqlite database nor an existing events.csv file (this only occurs if something goes wrong with migrateSQLite function), create a .csv
	f, err := os.OpenFile(EVENTPATH, os.O_CREATE|os.O_APPEND, 0644)

	if err != nil {
		log.Fatalln("writeToFile: Encountered an error while trying to create events.csv:", err)
	}

	defer f.Close()

	writer := csv.NewWriter(f)
	writer.Write([]string{"Filename", "Champion", "EventName", "EventTime", "Gamemode"})

	for _, e := range events {
		writer.Write([]string{filename, champ, e.Name, e.Time, mode})
	}

	writer.Flush()
	return nil
}

func getGameResult(client *http.Client) (result string, err error) {
	time.Sleep(3 * time.Second)

	if result, err := Exists(SETTINGSPATH); result == true && err == nil {
		var settings map[string]any

		f, err := os.ReadFile(SETTINGSPATH)

		if err != nil {
			log.Println("writeToFile: Failed to read settings file.", err)
			return "", err
		}

		err = json.Unmarshal(f, &settings)

		if err != nil {
			log.Println("writeToFile: Failed to unmarshal settings JSON file.", err)
			return "", err
		}

		var apiResponse map[string]any

		// request user PUUID from Riot API if it's not saved in settings yet, then update the file
		if settings["puuid"] == "" {
			body := map[string]any{"username": settings["username"], "tagline": settings["tagline"]}
			bodyJSON, err := json.Marshal(body)

			if err != nil {
				log.Println("writeToFile: Failed to marshal body for requesting PUUID!")
				return "", err
			}

			resp, err := client.Post("https://cxnf2smlr4hax5zunln6dte5iq0sobsi.lambda-url.us-east-2.on.aws/getpuuid", "application/json", bytes.NewReader(bodyJSON))

			if err != nil {
				log.Println("writeToFile: Failed to POST request for user PUUID!")
				return "", err
			}

			defer resp.Body.Close()

			if resp.StatusCode == http.StatusOK {
				err = json.NewDecoder(resp.Body).Decode(&apiResponse)

				if err != nil {
					log.Println("writeToFile: Failed to decode API response for User's PUUID!")
					return "", err
				}

				settings["puuid"] = apiResponse["puuid"]
			}

			settingsJSON, err := json.Marshal(settings)

			if err != nil {
				return "", err
			}

			err = os.WriteFile(SETTINGSPATH, settingsJSON, 0666)

			if err != nil {
				log.Println("getGameResult: Failed to write PUUID to settings file.")
				return "", err
			}
		}

		// request whether latest game was a win or loss
		body := map[string]any{"username": settings["username"], "tagline": settings["tagline"], "puuid": settings["tagline"]}
		bodyJSON, err := json.Marshal(body)

		if err != nil {
			log.Println("writeToFile: Failed to marshal body for requesting game result!")
			return "", err
		}

		resp, err := client.Post("https://cxnf2smlr4hax5zunln6dte5iq0sobsi.lambda-url.us-east-2.on.aws/getmatchresult", "application/json", bytes.NewReader(bodyJSON))

		if err != nil {
			log.Println("writeToFile: Failed to POST request for game result!")
			return "", err
		}

		defer resp.Body.Close()

		if resp.StatusCode == http.StatusOK {
			err = json.NewDecoder(resp.Body).Decode(&apiResponse)

			if err != nil {
				log.Println("writeToFile: Failed to decode API response for match result!")
				return "", err
			}
		}

		result, ok := apiResponse["result"].(string)

		if ok {
			return result, nil
		} else {
			return "", errors.New("Failed to convert result key of Riot API response to string.")
		}
	}

	return "", errors.New("Failed to check if SETTINGSPATH exists.")
}
