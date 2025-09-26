package main

import (
	"encoding/xml"
)

type FilteredGuardianItem struct {
	Title       string `json:"title"`
	Description string `json:"link_flair_text"`
	SourceURL   string `json:"source_url"`
}

type Guardianrss struct {
	Items []struct {
		Title       string `xml:"title"`
		Link        string `xml:"link"`
		Description string `xml:"description"`
	} `xml:"channel>item"`
}

func FilterGuardian(body []byte) ([]FilteredGuardianItem, error) {

	var feed Guardianrss
	if err := xml.Unmarshal(body, &feed); err != nil {
		return nil, err
	}

	var filtered []FilteredGuardianItem
	for _, it := range feed.Items {
		filtered = append(filtered, FilteredGuardianItem{
			Title:       it.Title,
			Description: it.Description,
			SourceURL:   it.Link,
		})
	}

	return filtered, nil
}
