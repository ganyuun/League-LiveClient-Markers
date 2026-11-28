package main

import (
	"context"
	"database/sql"
	"fmt"
	"log"
	"os"
	"os/exec"
	"slices"
	"strings"

	"golang.org/x/text/cases"
	"golang.org/x/text/language"

	_ "modernc.org/sqlite"
)

type VodService struct{}

func NewVodService() *VodService {
	return &VodService{}
}

func (g *VodService) ListVODs() []map[string]any {
	allVideos := []map[string]any{}

	db, err := sql.Open("sqlite", fmt.Sprintf("file:%s?_pragma=foreign_keys(1)", DBPATH))

	if err != nil {
		log.Fatal(err)
	}

	rows, err := db.Query("SELECT Filename, Champion, KDA, Gamemode, Result FROM videos ORDER BY Filename DESC")

	if err != nil {
		log.Fatal(err)
	}

	defer rows.Close()

	for rows.Next() {
		var filename, icon string
		var champion, kda, gamemode, result *string

		if err := rows.Scan(&filename, &champion, &kda, &gamemode, &result); err != nil {
			log.Print("ListVODs: ", err)
		}

		if champion != nil {
			if *champion == "MonkeyKing" || *champion == "Monkey King" {
				*champion = "Wukong"
				icon = "/ddragon/MonkeyKing.png"
			} else if strings.Contains(*champion, " ") {
				icon = fmt.Sprintf("/ddragon/%s.png", strings.ReplaceAll(*champion, " ", ""))
			} else if strings.Contains(*champion, "'") {
				replacedChamp := strings.ReplaceAll(*champion, "'", "")
				icon = fmt.Sprintf("/ddragon/%s.png", cases.Title(language.English).String(replacedChamp))
			} else {
				icon = fmt.Sprintf("/ddragon/%s.png", *champion)
			}
		}

		allVideos = append(allVideos, map[string]any{"Filename": filename, "Icon": icon, "Champion": champion, "KDA": kda, "Gamemode": gamemode, "Result": result})
	}

	if err := rows.Err(); err != nil {
		log.Print("ListVODs: Encountered error while querying for VODs! ", err)
	}

	return allVideos
}

func (g *VodService) GetFavorites() []string {
	favorites := []string{}

	db, err := sql.Open("sqlite", fmt.Sprintf("file:%s?_pragma=foreign_keys(1)", DBPATH))

	if err != nil {
		log.Fatal(err)
	}

	rows, err := db.Query("SELECT Filename FROM favorites")

	if err != nil {
		log.Fatal(err)
	}

	defer rows.Close()

	for rows.Next() {
		var filename string

		if err := rows.Scan(&filename); err != nil {
			break
		}

		favorites = append(favorites, filename)
	}

	if err := rows.Err(); err != nil {
		log.Print("GetFavorites: Encountered error while querying for favorites: ", err)
	}

	return favorites
}

func (g *VodService) UpdateFavorites(filename string) []string {
	db, err := sql.Open("sqlite", fmt.Sprintf("file:%s?_pragma=foreign_keys(1)", DBPATH))

	if err != nil {
		log.Fatalf("UpdateFavorites: %v", err)
	}

	if favorites := g.GetFavorites(); slices.Contains(favorites, filename) {
		db.Exec("DELETE FROM favorites WHERE Filename = (?)", filename)
		log.Printf("UpdateFavorites: Deleted %v from favorites.", filename)
	} else {
		db.Exec("INSERT INTO favorites VALUES (?)", filename)
		log.Printf("UpdateFavorites: Added %v to favorites.", filename)
	}

	return g.GetFavorites()
}

func (g *VodService) RemuxVODs() error {
	vodInfo, err := os.ReadDir(VODPATH)

	if err != nil {
		log.Printf("RemuxVODs: Failed to read %s: %v", VODPATH, err)
		return err
	}

	db, err := sql.Open("sqlite", fmt.Sprintf("file:%s?_pragma=foreign_keys(1)", DBPATH))

	if err != nil {
		log.Printf("RemuxVODs: Failed to open %s: %v", DBPATH, err)
		return err
	}

	ctx := context.Background()
	tx, err := db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelReadCommitted})
	defer tx.Rollback()

	if err != nil {
		log.Printf("RemuxVODs: Failed to begin transaction: %v", err)
		return err
	}

	// remux every non .mp4 so that it can be streamed in GUI
	for _, vod := range vodInfo {
		if !strings.Contains(vod.Name(), ".mp4") {
			oldPath := fmt.Sprintf("%s%s", VODPATH, vod.Name()) // ex. "./vods/something.mkv"
			baseName, _, _ := strings.Cut(vod.Name(), ".")      // "something"
			newName := fmt.Sprintf("%s.mp4", baseName)          // "something.mp4"
			newPath := fmt.Sprintf("%s%s", VODPATH, newName)    // ex. "./vods/something.mp4"

			cmd := exec.Command(FFMPEGPATH, "-i", oldPath, "-movflags", "+faststart", "-c", "copy", newPath)
			err := cmd.Run()

			if err != nil {
				log.Fatalf("RemuxVODs: Failed to remux %s: %v", vod.Name(), err)
				return err
			}

			_, err = tx.ExecContext(ctx, "UPDATE videos SET Filename = (?) WHERE Filename = (?)", newName, vod.Name())
			if err != nil {
				log.Printf("RemuxVODs: Failed to update videos table: %v", err)
				return err
			}

			err = os.Remove(oldPath)

			if err != nil {
				log.Printf("RemuxVODs: Failed to delete %s: %v", oldPath, err)
				return err
			}

			log.Printf("RemuxVODs: Successfully remuxed: %s -> %s.", oldPath, newPath)
		}
	}

	if err := tx.Commit(); err != nil {
		log.Printf("RemuxVODs: Failed to commit transaction: %s", err)
		return err
	}

	return nil
}

func (g *VodService) ListEvents(filename string) []map[string]any {
	events := []map[string]any{}

	db, err := sql.Open("sqlite", fmt.Sprintf("file:%s?_pragma=foreign_keys(1)", DBPATH))

	if err != nil {
		log.Fatal(err)
	}

	rows, err := db.Query("SELECT ROW_NUMBER() OVER (ORDER BY EventTime) AS Row, EventName, EventTime FROM 'events' WHERE Filename = (?) ORDER BY Row", filename)

	if err != nil {
		log.Printf("GetEvents: Failed to get events for %s: %v", filename, err)
		return events
	}

	for rows.Next() {
		var row int
		var name string
		var time float64

		err := rows.Scan(&row, &name, &time)

		if err != nil {
			log.Printf("GetEvents: Error in rows.Next() loop: %v", err)
		}

		events = append(events, map[string]any{"Row": row, "EventName": name, "EventTime": time})
	}

	if err := rows.Err(); err != nil {
		log.Print("GetEvents: Encountered error while querying for VODs! ", err)
	}

	return events
}
