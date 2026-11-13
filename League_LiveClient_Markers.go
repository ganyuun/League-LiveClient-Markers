package main

import (
	"encoding/json/v2"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"strconv"
	"time"

	"github.com/andreykaipov/goobs"
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

var LOGPATH string = fmt.Sprintf("./data/logs/log %s.txt", time.Now().Format("2006-01-02"))

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

func obsWebsocketCredentials() (int, string, error) {
	port, errPort := keyring.Get("LiveClient", "port")
	password, errPassword := keyring.Get("LiveClient", "websocketPassword")

	if errPort != nil || errPassword != nil {
		fmt.Println("Secrets not found!")

		result, err := Exists("./obs/config/obs-studio/plugin_config/obs-websocket")

		if err != nil {
			panic(err)
		}

		if result == true {
			type response struct {
				Server_password string `json:"server_password"`
				Server_port     int    `json:"server_port"`
			}

			f, err := os.ReadFile("./obs/config/obs-studio/plugin_config/obs-websocket/config.json")

			if err != nil {
				panic(err)
			}

			var config response
			json.Unmarshal(f, &config)

			var port = config.Server_port
			var password = config.Server_password

			err = keyring.Set("LiveClient", "port", strconv.Itoa(port))

			if err != nil {
				panic(err)
			}

			err = keyring.Set("LiveClient", "websocketPassword", password)

			if err != nil {
				panic(err)
			}

			return port, password, nil
		}
	}

	portInt, err := strconv.Atoi(port)

	if err != nil {
		panic(err)
	}

	return portInt, password, nil
}

func main() {
	port, password, err := obsWebsocketCredentials()

	if err != nil {
		panic(err)
	}

	client, err := goobs.New(fmt.Sprintf("localhost:%d", port), goobs.WithPassword(password))

	if err != nil {
		panic(err)
	}

	outputs, err := client.Outputs.GetOutputList()

	type ObsOutput struct {
		OutputActive bool `json:"outputActive"`
	}

	var status ObsOutput

	json.Unmarshal(outputs.GetRaw(), status)

	fmt.Println("Is OBS recording?", status.OutputActive)

	if err := MigrateSQLite(); err == nil {
		fmt.Println("Migration successful")
	} else {
		fmt.Println("Migration failed", err)
	}
}
