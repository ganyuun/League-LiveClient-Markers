package main

import (
	"fmt"
	"net"
	"net/http"
	"path/filepath"
	"strings"
)

type MediaService struct {
	baseURL string
}

func NewMediaService() (*MediaService, error) {
	mux := http.NewServeMux()

	vodFs := http.FileServer(http.Dir(VODPATH))
	mux.Handle("/vods/", http.StripPrefix("/vods/", http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		vodFs.ServeHTTP(w, r)
	})))

	clipFs := http.FileServer(http.Dir(CLIPPATH))
	mux.Handle("/clips/", http.StripPrefix("/clips/", http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		clipFs.ServeHTTP(w, r)
	})))

	listener, err := net.Listen("tcp", "127.0.0.1:0")

	if err != nil {
		return nil, err
	}

	go http.Serve(listener, mux)

	return &MediaService{
		baseURL: fmt.Sprintf("http://127.0.0.1:%d", listener.Addr().(*net.TCPAddr).Port),
	}, nil
}

func (m *MediaService) GetVodURL(filename string) string {
	clean := filepath.Base(filename)
	return fmt.Sprintf("%s/vods/%s", strings.TrimRight(m.baseURL, "/"), clean)
}

func (m *MediaService) GetClipURL(filename string) string {
	clean := filepath.Base(filename)
	return fmt.Sprintf("%s/clips/%s", strings.TrimRight(m.baseURL, "/"), clean)
}
