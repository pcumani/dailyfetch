package main

import (
	"context"

	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"sync"

	"github.com/joho/godotenv"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

var (
	host  = flag.String("host", "0.0.0.0", "host to connect to/listen on")
	port  = flag.Int("port", 8000, "port number to connect to/listen on")
	proto = flag.String("proto", "http", "if set, use as proto:// part of URL (ignored for server)")
)

type NewsResult struct {
	Source string `json:"source"`
	Data   any    `json:"data"`
}

type NewsInput struct {
	Sources []string `json:"sources" jsonschema:"list of sources such as 'hn', 'reddit'"`
}

func fetchURL(url, source string, wg *sync.WaitGroup, ch chan<- NewsResult) {
	defer wg.Done()
	resp, err := http.Get(url)
	if err != nil {
		ch <- NewsResult{Source: source, Data: "Error: " + err.Error()}
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		ch <- NewsResult{
			Source: source,
			Data:   fmt.Sprintf("Error: HTTP status code %d. %s", resp.StatusCode, string(body)),
		}
		return
	}

	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusOK {
		ch <- NewsResult{
			Source: source,
			Data:   fmt.Sprintf("HTTP error %d: %s", resp.StatusCode, string(body)),
		}
		return
	}
	if len(body) == 0 {
		ch <- NewsResult{Source: source, Data: "error: empty response body"}
		return
	}

	var filtered any
	switch source {
	case "reddit":
		filteredArr, err := FilterRedditJSON(body)
		if err != nil {
			ch <- NewsResult{Source: source, Data: "error: " + err.Error()}
			return
		}
		filtered = filteredArr
	default:
		filtered = string(body)
	}

	ch <- NewsResult{Source: source, Data: filtered}

}

func fetchNews(ctx context.Context, req *mcp.CallToolRequest, input NewsInput) (*mcp.CallToolResult, any, error) {

	sourcesRaw := input.Sources
	if len(sourcesRaw) == 0 {
		sourcesRaw = []string{"reddit"} // default
	}
	newsAPIKey := os.Getenv("NEWS_API")

	var wg sync.WaitGroup
	ch := make(chan NewsResult, len(sourcesRaw))

	for _, s := range sourcesRaw {
		src := s
		wg.Add(1)
		switch src {
		case "hn":
			hnURL := fmt.Sprintf("https://newsapi.org/v2/top-headlines?country=us&category=technology&apiKey=%s", newsAPIKey)
			go fetchURL(hnURL, "hackernews", &wg, ch)
		case "reddit":
			go fetchURL("https://www.reddit.com/r/technology/top.json?limit=5", "reddit", &wg, ch)
		default:
			wg.Done()
		}
	}

	wg.Wait()
	close(ch)

	results := []NewsResult{}
	for res := range ch {
		results = append(results, res)
	}

	// Print each NewsResult
	for _, r := range results {
		fmt.Printf("Source: %s - Data: %v\n\n", r.Source, fmt.Sprint(r.Data)[:50])
	}

	// Return as a dictionary/object
	return nil, map[string]any{"results": results}, nil
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("OK"))
}

func main() {
	flag.Parse()

	// Load .env file for NEWS_API
	if err := godotenv.Load(); err != nil {
		log.Printf("Warning: .env file not loaded (%v)", err)
	}

	server := mcp.NewServer(&mcp.Implementation{Name: "news_fetcher"}, nil)

	mcp.AddTool(server, &mcp.Tool{Name: "news_fetcher", Description: "Retrieves news from several sources"}, fetchNews)

	url := fmt.Sprintf("%s:%d", *host, *port)

	// Create the streamable HTTP handler.
	handler := mcp.NewStreamableHTTPHandler(func(req *http.Request) *mcp.Server {
		return server
	}, nil)

	handlerWithLogging := loggingHandler(handler)

	// Create a mux to handle /health and MCP endpoints
	mux := http.NewServeMux()
	mux.Handle("/health", http.HandlerFunc(healthHandler))
	mux.Handle("/", handlerWithLogging)

	log.Printf("MCP server listening on %s", url)
	log.Printf("Available tool: news_fetcher (Sources: 'hn', 'reddit')")

	// Start the HTTP server with logging handler.
	if err := http.ListenAndServe(url, mux); err != nil {
		log.Fatalf("Server failed: %v", err)
	}

}
