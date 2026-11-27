package main

import (
	"context"
	"database/sql"
	"fmt"
	"log"
	"os"

	"github.com/wailsapp/wails/v3/pkg/application"

	_ "modernc.org/sqlite"
)

type FileService struct{}

func NewFileService() *FileService {
	return &FileService{}
}

func (g *FileService) DeleteFile(folder string, filename string) (deleted bool) {
	path := fmt.Sprintf("%s/%s/%s", ROOT, folder, filename)

	if folder == "vods" {
		db, err := sql.Open("sqlite", fmt.Sprintf("file:%s?_pragma=foreign_keys(1)", DBPATH))

		if err != nil {
			log.Printf("DeleteFile: Failed to open database: %v", err)
			return false
		}

		ctx := context.Background()
		tx, err := db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelReadCommitted})

		_, err = tx.Exec("DELETE FROM videos WHERE Filename = (?)", filename)

		if err != nil {
			log.Printf("DeleteFile: Failed to delete %s from database: %v", filename, err)
			tx.Rollback()
			return false
		}

		err = os.Remove(path)

		if err != nil {
			log.Printf("DeleteFile: Failed to delete %s: %v", filename, err)
			tx.Rollback()
			return false
		}

		if err = tx.Commit(); err != nil {
			tx.Rollback()
			log.Printf("DeleteFile: Failed to commit transaction to delete  %s from database: %v", filename, err)
			return false
		}

		log.Printf("DeleteFile: Deleted %v successfully.", path)
		return true
	}

	err := os.Remove(path)

	if err != nil {
		log.Printf("DeleteFile: Failed to delete %s: %v", filename, err)
		return false
	}

	log.Printf("DeleteFile: Deleted %v successfully.", path)
	return true
}

func (g *FileService) RevealFile(folder string, filename string) {
	relPath := fmt.Sprintf("%s/%s/%s", ROOT, folder, filename)
	application.Get().Env.OpenFileManager(relPath, true)
}
