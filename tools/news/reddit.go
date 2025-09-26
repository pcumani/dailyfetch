package main

import (
	"encoding/json"
)

// Struct to match the fields we want
type FilteredRedditItem struct {
	Subreddit           string `json:"subreddit"`
	Title               string `json:"title"`
	LinkFlairText       string `json:"link_flair_text"`
	Domain              string `json:"domain"`
	URLOverriddenByDest string `json:"url_overridden_by_dest"`
	Permalink           string `json:"permalink"`
	URL                 string `json:"url"`
}

// Reddit API top-level response
type RedditResponse struct {
	Data struct {
		Children []struct {
			Data map[string]interface{} `json:"data"`
		} `json:"children"`
	} `json:"data"`
}

// Function: takes raw JSON bytes, returns filtered slice
func FilterRedditJSON(body []byte) ([]FilteredRedditItem, error) {
	var resp RedditResponse
	if err := json.Unmarshal(body, &resp); err != nil {
		return nil, err
	}

	var filtered []FilteredRedditItem
	for _, child := range resp.Data.Children {
		item := child.Data
		filtered = append(filtered, FilteredRedditItem{
			Subreddit:           getString(item, "subreddit"),
			Title:               getString(item, "title"),
			LinkFlairText:       getString(item, "link_flair_text"),
			Domain:              getString(item, "domain"),
			URLOverriddenByDest: getString(item, "url_overridden_by_dest"),
			Permalink:           getString(item, "permalink"),
			URL:                 getString(item, "url"),
		})
	}

	return filtered, nil
}

// Optional: helper to marshal filtered items to JSON string
func MarshalFilteredItems(items []FilteredRedditItem) (string, error) {
	out, err := json.MarshalIndent(items, "", "  ")
	if err != nil {
		return "", err
	}
	return string(out), nil
}

// Helper to safely extract string fields
func getString(m map[string]interface{}, key string) string {
	if val, ok := m[key]; ok {
		if str, ok := val.(string); ok {
			return str
		}
	}
	return ""
}
