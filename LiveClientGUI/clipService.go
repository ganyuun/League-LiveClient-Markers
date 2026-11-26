package main

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"slices"
	"strings"

	_ "modernc.org/sqlite"
)

type ClipService struct{}

func NewClipService() *ClipService {
	return &ClipService{}
}

type clipInfo struct {
	ClipPath  string
	Filename  string
	Thumbnail string
}

var FFPROBEPATH string = fmt.Sprintf("%s/ffprobe.exe", ROOT)
var FFMPEGPATH string = fmt.Sprintf("%s/ffmpeg.exe", ROOT)

func (g *ClipService) ListClips() []clipInfo {
	clipDir, err := os.ReadDir(CLIPPATH)
	clips := []string{}

	if err != nil {
		log.Print("ListClips: Error reading CLIPPATH directory: ", err)
	}

	for _, file := range clipDir {
		if !file.IsDir() {
			clips = append(clips, file.Name())
		}
	}

	// clipDir goes from oldest to newest by default, want to show the newest clips first
	slices.Reverse(clips)

	thumbDir, err := os.ReadDir(THUMBPATH)
	thumbs := []string{}

	if err != nil {
		log.Print("ListClips: Error reading THUMBPATH directory: ", err)
	}

	for _, file := range thumbDir {
		if !file.IsDir() {
			thumbs = append(thumbs, file.Name())
		}
	}

	clipsThumbs := []clipInfo{}

	for _, file := range clips {
		baseFilename, _, _ := strings.Cut(file, ".")
		var thumbName string = fmt.Sprintf("%s.webp", baseFilename)

		if !slices.Contains(thumbs, thumbName) {
			cmd := exec.Command(FFMPEGPATH, "-y", "-ss", "00:00:01", "-i", fmt.Sprintf("%s/clips/%s", ROOT, file), "-frames:v", "1", fmt.Sprintf("%s/data/thumbnails/%s", ROOT, thumbName), "-loglevel", "error")
			out, err := cmd.CombinedOutput()

			if err != nil {
				log.Printf("clipInfo: Error while generating thumbnail! %v, %v", out, err)
				clipsThumbs = append(clipsThumbs, clipInfo{Filename: file, Thumbnail: ""})
				continue
			}
		}

		clipsThumbs = append(clipsThumbs, clipInfo{ClipPath: fmt.Sprintf("%s/clips/%s", ROOT, file), Filename: file, Thumbnail: fmt.Sprintf("/thumbs/%s", thumbName)})
	}

	return clipsThumbs
}
