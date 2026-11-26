package main

import (
	"database/sql"
	"fmt"
	"log"
	"slices"
	"strings"

	"golang.org/x/text/cases"
	"golang.org/x/text/language"

	_ "modernc.org/sqlite"
)

type VodListService struct{}

func NewVodListService() *VodListService {
	return &VodListService{}
}

func (g *VodListService) ListVODs() []map[string]any {
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

func (g *VodListService) GetFavorites() []string {
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

func (g *VodListService) UpdateFavorites(filename string) []string {
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
