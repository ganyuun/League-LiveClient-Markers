package main

import (
	"context"
	"database/sql"
	"encoding/csv"
	"fmt"
	"io"
	"log"
	"os"
	"slices"

	"github.com/gocarina/gocsv"
	_ "modernc.org/sqlite"
)

type event struct {
	File      string `csv:"Filename"`
	Champ     string `csv:"Champion"`
	EventName string `csv:"EventName"`
	EventTime string `csv:"EventTime"`
	Gamemode  string `csv:"Gamemode"`
}

func Filter[T any](slice []T, predicate func(T) bool) []T {
	var result []T

	for _, v := range slice {
		if predicate(v) {
			result = append(result, v)
		}
	}
	return result
}

func MigrateSQLite() (bool, error) {
	logFile, err := os.OpenFile(LOGPATH, os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0644)

	if err != nil {
		panic(err)
	}

	logWriter := io.MultiWriter(os.Stdout, logFile)
	log.SetOutput(logWriter)

	if result, err := Exists(DBPATH); result == false && err == nil {
		log.Print("\t--- CSV -> SQLite3 Migration ---")

		videos, err := os.ReadDir(VODPATH)

		log.Printf("There are %d video(s) in the VODs directory.", len(videos))

		os.Create(DBPATH)

		db, err := sql.Open("sqlite", fmt.Sprintf("file:%s?_pragma=foreign_keys(1)", DBPATH))
		if err != nil {
			return true, err
		}

		_, err = db.Exec(`
			CREATE TABLE IF NOT EXISTS videos(
				Filename TEXT NOT NULL PRIMARY KEY,
				Champion TEXT,
				KDA TEXT,
				Gamemode TEXT,
				Result TEXT,
				Status TEXT DEFAULT 'Active',
				Expires TIMESTAMP DEFAULT NULL
			);
		`)

		_, err = db.Exec(`
			CREATE TABLE IF NOT EXISTS events(
				Filename TEXT,
				EventName TEXT,
				EventTime TEXT,
				FOREIGN KEY (Filename) REFERENCES videos(Filename)
					ON DELETE CASCADE
			);
		`)

		_, err = db.Exec(`
			CREATE TABLE IF NOT EXISTS favorites( 
				Filename TEXT PRIMARY KEY,
				FOREIGN KEY (Filename) REFERENCES videos(Filename)
					ON DELETE CASCADE
			);
		`)

		_, err = db.Exec(`
			CREATE TRIGGER IF NOT EXISTS setExpireDate 
			AFTER UPDATE OF Status ON videos
			FOR EACH ROW WHEN NEW.Status = 'Trash'
			BEGIN
				UPDATE videos
				SET Expires = date('now', '+7 days')
				WHERE Filename = NEW.Filename;
			END;
		`)

		_, err = db.Exec(`
			CREATE TRIGGER IF NOT EXISTS removeExpireDate 
			AFTER UPDATE OF Status ON videos
			FOR EACH ROW WHEN NEW.Status != 'Trash'
			BEGIN
				UPDATE videos
				SET Expires = NULL
				WHERE Filename = NEW.Filename;
			END;
		`)

		ctx := context.Background()

		if err != nil {
			log.Print("Failed to begin transaction:", err)
			return true, err
		}

		if result, err := Exists(EVENTPATH); result == true && err == nil {
			eventFile, err := os.Open(EVENTPATH)
			if err != nil {
				return true, err
			}
			defer eventFile.Close()

			events := []*event{}

			if err := gocsv.UnmarshalFile(eventFile, &events); err != nil {
				return true, err
			}

			videoTx, err := db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelReadCommitted})

			// populating videos table
			for _, video := range videos {
				log.Printf("Currently working on %s for video table.\n", video.Name())

				filtered := Filter(events, func(event *event) bool {
					return event.File == video.Name()
				})

				if len(filtered) > 0 {
					log.Printf("\tFound %d events for %s\n", len(filtered), video.Name())

					killCount := len(Filter(filtered, func(event *event) bool {
						return event.EventName == "ChampionKill"
					}))
					deathCount := len(Filter(filtered, func(event *event) bool {
						return event.EventName == "Death"
					}))
					assistCount := len(Filter(filtered, func(event *event) bool {
						return event.EventName == "Assist"
					}))

					log.Printf("\tFound the following KDA for %s: %d/%d/%d\n", video.Name(), killCount, deathCount, assistCount)

					_, err = videoTx.ExecContext(
						ctx,
						`INSERT INTO videos (Filename, Champion, KDA, Gamemode) 
						VALUES (?, ?, ?, ?)`,
						filtered[0].File,
						filtered[0].Champ,
						fmt.Sprintf("%d/%d/%d", killCount, deathCount, assistCount),
						filtered[0].Gamemode)
				} else {
					_, err = videoTx.ExecContext(
						ctx,
						`INSERT INTO videos (Filename)
						VALUES (?)`, video.Name())
				}
			}

			if err = videoTx.Commit(); err != nil {
				videoTx.Rollback()
				log.Print("Failed to insert videos! Transaction rolled back. ", err)
			}
			log.Print("Finished adding videos!")

			eventTx, err := db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelReadCommitted})

			// populating events table
			for _, event := range events {
				_, err = eventTx.ExecContext(
					ctx,
					`INSERT INTO events (Filename, EventName, EventTime) 
					VALUES (?, ?, ?)`,
					event.File, event.EventName, event.EventTime)
			}

			if err = eventTx.Commit(); err != nil {
				eventTx.Rollback()
				log.Print("Failed to insert all events! Transaction rolled back. ", err)
			}

			log.Print("Finished adding events!")

		} else if err != nil {
			fmt.Print("migrateSQLite: Failed at EVENTPATH ", err)
			return true, err
		}

		// populating favorites
		if result, err := Exists(FAVSPATH); result == true && err == nil {
			f, err := os.OpenFile(FAVSPATH, os.O_RDONLY, 0644)

			if err != nil {
				return true, err
			}

			defer f.Close()

			r := csv.NewReader(f)
			favorites, err := r.ReadAll()

			if err != nil {
				log.Fatal("MigrateSQLite: Failed to read all lines in favoritedVODs.csv: ", err)
			}

			favTx, err := db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelReadCommitted})

			videoStrings := make([]string, len(videos))

			for i := range videos {
				videoStrings[i] = videos[i].Name()
			}

			for _, fav := range favorites[1:] {
				if slices.Contains(videoStrings, fav[0]) {
					_, err = favTx.ExecContext(
						ctx,
						`INSERT INTO favorites (Filename)
						VALUES (?)`, fav[0])
				}
			}

			if err = favTx.Commit(); err != nil {
				favTx.Rollback()
				log.Print("Failed to insert all favorites! Transaction rolled back. ", err)
			}

			log.Print("Finished adding favorites!\n")
		} else if err != nil {
			log.Print("Failed at FAVSPATH ", err)
			return true, err
		}

		db.Close()
	}

	return false, nil
}
