package main

import (
	"embed"
	"errors"
	"fmt"
	"io/fs"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"log"

	"github.com/wailsapp/wails/v3/pkg/application"
)

//go:embed all:frontend/dist
var assets embed.FS

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

func getRoot() string {
	_, err := os.Stat(filepath.Join(".", "ddragon", "Shyvana"))

	if err == nil {
		log.Print("main: Root set to .")
		return "."
	}

	return ".."
}

var ROOT string = getRoot()
var VODPATH string = fmt.Sprintf("%s/vods/", ROOT)
var EVENTPATH string = fmt.Sprintf("%s/data/events.csv", ROOT)
var DBPATH string = fmt.Sprintf("%s/data/data.db", ROOT)
var SETTINGSPATH string = fmt.Sprintf("%s/data/settings.json", ROOT)
var CLIPPATH string = fmt.Sprintf("%s/clips/", ROOT)
var THUMBPATH string = fmt.Sprintf("%s/data/thumbnails/", ROOT)
var FAVSPATH string = fmt.Sprintf("%s/data/favoritedVODs.csv", ROOT)
var LOGPATH string = fmt.Sprintf("%s/data/logs/log %s.txt", ROOT, time.Now().Format("01-02-2006"))
var FFPROBEPATH string = fmt.Sprintf("%s/ffprobe.exe", ROOT)
var FFMPEGPATH string = fmt.Sprintf("%s/ffmpeg.exe", ROOT)

func assetMiddleware() application.Middleware {
	ddragonServe := http.StripPrefix("/ddragon/", http.FileServer(http.Dir(filepath.Join(ROOT, "ddragon"))))
	thumbServe := http.StripPrefix("/thumbs/", http.FileServer(http.Dir(filepath.Join(ROOT, "data", "thumbnails"))))

	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if strings.HasPrefix(r.URL.Path, "/wails") {
				next.ServeHTTP(w, r)
				return
			} else if strings.HasPrefix(r.URL.Path, "/ddragon") {
				ddragonServe.ServeHTTP(w, r)
				return
			} else if strings.HasPrefix(r.URL.Path, "/thumbs") {
				thumbServe.ServeHTTP(w, r)
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}

func main() {
	mediaService, err := NewMediaService()
	if err != nil {
		log.Fatal(err)
	}

	app := application.New(application.Options{
		Name:        "LiveClient",
		Description: "Getting events from Riot's Live Client API!",
		Services: []application.Service{
			application.NewService(mediaService),
			application.NewService(NewVodService()),
			application.NewService(NewClipService()),
			application.NewService(NewFileService()),
		},
		Assets: application.AssetOptions{
			Handler:    application.AssetFileServerFS(assets),
			Middleware: assetMiddleware(),
		},
	})

	app.Window.NewWithOptions(application.WebviewWindowOptions{
		Title:            "LiveClient",
		Width:            1100,
		Height:           700,
		MinWidth:         900,
		MinHeight:        500,
		BackgroundColour: application.NewRGB(6, 7, 15),
		URL:              "/",
	})

	if migrationNeeded, err := MigrateSQLite(); err == nil {
		if migrationNeeded == true {
			fmt.Println("main: Migration from .csv to SQLite3 successful")
		}
	} else {
		log.Fatal(err)
	}

	if migrationNeeded, err := MigrateSQLite(); err == nil {
		if migrationNeeded == true {
			log.Print("Main: SQLite migration successful")
		}
	} else {
		log.Fatal(err)
	}

	if err := NewVodService().RemuxVODs(); err != nil {
		log.Fatal(err)
	}

	if len(os.Args) > 1 {
		switch os.Args[1] {
		case "gui":
			err := app.Run()

			if err != nil {
				log.Fatal(err)
			}
		case "markers":
			StartMarkers()
		}
	} else {
		err := app.Run()

		if err != nil {
			log.Fatal(err)
		}
	}
}
