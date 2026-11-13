package main

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"slices"

	"github.com/gocarina/gocsv"
	_ "modernc.org/sqlite"
)

type Event struct {
	File      string `csv:"Filename"`
	Champ     string `csv:"Champion"`
	EventName string `csv:"EventName"`
	EventTime string `csv:"EventTime"`
	Gamemode  string `csv:"Gamemode"`
}

type Favorite struct {
	File string `csv:"Name"`
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

func MigrateSQLite() error {
	if result, err := Exists(DBPATH); result == false && err == nil {
		fmt.Println("\n--- CSV -> SQLite3 Migration ---\n")

		videos, err := os.ReadDir(VODPATH)

		fmt.Println("There are", len(videos), "videos in the VODs directory")

		os.Create(DBPATH)

		db, err := sql.Open("sqlite", fmt.Sprintf("file:%s?_pragma=foreign_keys(1)", DBPATH))
		if err != nil {
			return err
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
			fmt.Println("Failed to begin transaction:", err)
			return err
		}

		if result, err := Exists(EVENTPATH); result == true && err == nil {
			eventFile, err := os.Open(EVENTPATH)
			if err != nil {
				return err
			}
			defer eventFile.Close()

			events := []*Event{}

			if err := gocsv.UnmarshalFile(eventFile, &events); err != nil {
				return err
			}

			videoTx, err := db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelReadCommitted})

			// populating videos table
			for _, video := range videos {
				fmt.Printf("Currently working on %s for video table.\n", video.Name())

				filtered := Filter(events, func(event *Event) bool {
					return event.File == video.Name()
				})

				if len(filtered) > 0 {
					fmt.Printf("\tFound %d events for %s\n", len(filtered), video.Name())

					killCount := len(Filter(filtered, func(event *Event) bool {
						return event.EventName == "ChampionKill"
					}))
					deathCount := len(Filter(filtered, func(event *Event) bool {
						return event.EventName == "Death"
					}))
					assistCount := len(Filter(filtered, func(event *Event) bool {
						return event.EventName == "Assist"
					}))

					fmt.Printf("\tFound the following KDA for %s: %d/%d/%d\n", video.Name(), killCount, deathCount, assistCount)

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
				fmt.Println("Failed to insert videos! Transaction rolled back.", err)
			}
			fmt.Println("Finished adding videos!")

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
				fmt.Println("Failed to insert all events! Transaction rolled back.", err)
			}

			fmt.Println("Finished adding events!")

		} else if err != nil {
			fmt.Println("Failed at EVENTPATH")
			return err
		}

		if result, err := Exists(FAVSPATH); result == true && err == nil {
			favsFile, err := os.Open(FAVSPATH)

			if err != nil {
				return err
			}

			defer favsFile.Close()

			favorites := []*Favorite{}

			if err := gocsv.UnmarshalFile(favsFile, &favorites); err != nil {
				return err
			} else {
				favTx, err := db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelReadCommitted})

				videoStrings := make([]string, len(videos))

				for i := range videos {
					videoStrings[i] = videos[i].Name()
				}

				for i := range favorites {
					if slices.Contains(videoStrings, favorites[i].File) {
						_, err = favTx.ExecContext(
							ctx,
							`INSERT INTO favorites (Filename)
							VALUES (?)`, favorites[i].File)
					}
				}

				if err = favTx.Commit(); err != nil {
					favTx.Rollback()
					fmt.Println("Failed to insert all favorites! Transaction rolled back.", err)
				}
			}
		} else if err != nil {
			fmt.Println("Failed at FAVSPATH")
			return err
		}

		db.Close()
	}

	return nil
}
