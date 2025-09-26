package main

import (
	"encoding/xml"
)

// Struct to match the fields we want
type FilteredGNItem struct {
	Title       string `json:"title"`
	Description string `json:"link_flair_text"`
	SourceName  string `json:"domain"`
	SourceURL   string `json:"source_url"`
}

type GNrss struct {
	Items []struct {
		Title       string `xml:"title"`
		Description string `xml:"description"`
		Source      struct {
			Name string `xml:",chardata"`
			URL  string `xml:"url,attr"`
		} `xml:"source"`
	} `xml:"channel>item"`
}

func FilterGN(body []byte) ([]FilteredGNItem, error) {

	var feed GNrss
	if err := xml.Unmarshal(body, &feed); err != nil {
		return nil, err
	}

	// Map to []FilteredItem
	var filtered []FilteredGNItem
	for _, it := range feed.Items {
		filtered = append(filtered, FilteredGNItem{
			Title:       it.Title,
			Description: it.Description,
			SourceName:  it.Source.Name,
			SourceURL:   it.Source.URL,
		})
	}

	return filtered, nil
}
