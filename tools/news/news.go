package main

import (
	"context"
	"time"

	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"sync"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

var (
	host  = flag.String("host", "0.0.0.0", "host to connect to/listen on")
	port  = flag.Int("port", 8000, "port number to connect to/listen on")
	proto = flag.String("proto", "http", "if set, use as proto:// part of URL (ignored for server)")
)

type NewsResult struct {
	Source   string `json:"source"`
	Category string `json:"category"`
	Data     any    `json:"data"`
	Error    string `json:"error"`
}

type NewsInput struct {
	Sources    []string `json:"sources" jsonschema:"list of sources such as 'newsapi', 'reddit', 'googlenews'"`
	Categories []string `json:"categories" jsonschema:"list of categories such as 'technology', 'sport', 'general'"`
}

func fetchURL(url, source string, category string, wg *sync.WaitGroup, ch chan<- NewsResult) {
	defer wg.Done()

	// Create the request
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		ch <- NewsResult{Source: source, Category: category, Error: "Error creating request: " + err.Error()}
		return
	}

	// Add User-Agent header to avoid strict limits and 429 errors
	req.Header.Set("User-Agent", "DailyFetch/1.0")

	// Execute request
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		ch <- NewsResult{Source: source, Category: category, Error: "Error: " + err.Error()}
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		ch <- NewsResult{
			Source:   source,
			Category: category,
			Error:    fmt.Sprintf("Error HTTP (%d): %s", resp.StatusCode, string(body)),
		}
		return
	}

	body, _ := io.ReadAll(resp.Body)

	if len(body) == 0 {
		ch <- NewsResult{Source: source, Category: category, Error: "Error: empty response body"}
		return
	}

	var filtered any
	switch source {
	case "reddit":
		filteredArr, err := FilterRedditJSON(body)
		if err != nil {
			ch <- NewsResult{Source: source, Category: category, Error: "Error: " + err.Error()}
			return
		}
		filtered = filteredArr
	case "googlenews":
		filteredArr, err := FilterGN(body)
		if err != nil {
			ch <- NewsResult{Source: source, Category: category, Error: "Error: " + err.Error()}
			return
		}
		filtered = filteredArr
	case "guardian":
		filteredArr, err := FilterGuardian(body)
		if err != nil {
			ch <- NewsResult{Source: source, Category: category, Error: "Error: " + err.Error()}
			return
		}
		filtered = filteredArr
	default:
		filtered = string(body)
	}

	ch <- NewsResult{Source: source, Category: category, Data: filtered}

}

func fetchNews(ctx context.Context, req *mcp.CallToolRequest, input NewsInput) (*mcp.CallToolResult, any, error) {

	sourcesRaw := input.Sources
	if len(sourcesRaw) == 0 {
		sourcesRaw = []string{"reddit"} // default
	}

	categoriesRaw := input.Categories
	if len(categoriesRaw) == 0 {
		categoriesRaw = []string{"general"} // default
	}

	var wg sync.WaitGroup
	ch := make(chan NewsResult, len(sourcesRaw)*len(categoriesRaw))

	// Launch one goroutine per (category, source) combination
	for i, cat := range categoriesRaw {

		for _, src := range sourcesRaw {
			wg.Add(1)
			switch src {
			case "guardian":
				var gURL string
				switch cat {
				case "entertainment":
					gURL = "https://www.theguardian.com/uk/culture/rss"
				case "general":
					gURL = "https://www.theguardian.com/uk/rss"
				case "science":
					gURL = "https://www.theguardian.com/science/rss"
				default:
					gURL = fmt.Sprintf("https://www.theguardian.com/uk/%s/rss", cat)
				}

				go fetchURL(gURL, src, cat, &wg, ch)
			case "reddit":
				catr := cat
				switch cat {
				case "general":
					catr = "news"
				case "sport":
					catr = "sports"
				}

				redURL := fmt.Sprintf("https://www.reddit.com/r/%s/top.json?limit=5", catr)
				go fetchURL(redURL, src, cat, &wg, ch)
			case "googlenews":
				googURL := fmt.Sprintf("https://news.google.com/rss/search?hl=en-US&gl=US&ceid=US-en&q=%s", cat)
				go fetchURL(googURL, src, cat, &wg, ch)
			default:
				wg.Done()
			}
		}

		// wait some time before next category (skip after last one) to not overload APIs
		if i < len(categoriesRaw)-1 {
			time.Sleep(1 * time.Second)
		}
	}

	wg.Wait()
	close(ch)

	// resultsMap: category → source → NewsResult
	resultsMap := make(map[string]map[string]NewsResult)

	for res := range ch {
		if _, ok := resultsMap[res.Category]; !ok {
			resultsMap[res.Category] = make(map[string]NewsResult)
		}
		resultsMap[res.Category][res.Source] = res
	}

	// Print each NewsResult
	for cat, sources := range resultsMap {
		fmt.Printf("Category: %s\n", cat)
		for src, res := range sources {
			if res.Data == nil {
				fmt.Printf(" Source: %s - Error: %+v\n", src, res.Error)
			} else {
				fmt.Printf(" Source: %s - Data: %v entries\n", src, res.Data)
			}
		}
	}

	// Return as a dictionary/object
	return nil, map[string]any{"results": resultsMap}, nil
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("OK"))
}

func main() {
	flag.Parse()

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
	log.Printf("Available tool: news_fetcher (Sources: 'googlenews', 'guardian' 'reddit', Categories: 'technology', 'business', 'entertainment', 'science', 'sport', 'general')")

	// Start the HTTP server with logging handler.
	if err := http.ListenAndServe(url, mux); err != nil {
		log.Fatalf("Server failed: %v", err)
	}

}
