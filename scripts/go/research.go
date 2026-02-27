package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"
)

type SearchResult struct {
	Title   string `json:"title"`
	URL     string `json:"url"`
	Snippet string `json:"snippet"`
}

type GeminiRequest struct {
	Contents         []Content `json:"contents"`
	Tools            []Tool    `json:"tools"`
	GenerationConfig Config    `json:"generationConfig"`
}

type Content struct {
	Role  string `json:"role"`
	Parts []Part `json:"parts"`
}

type Part struct {
	Text string `json:"text"`
}

type Tool struct {
	GoogleSearch map[string]interface{} `json:"googleSearch"`
}

type Config struct {
	Temperature     float64 `json:"temperature"`
	MaxOutputTokens int     `json:"maxOutputTokens"`
}

type GeminiResponse struct {
	Candidates []Candidate `json:"candidates"`
}

type Candidate struct {
	GroundingMetadata GroundingMetadata `json:"groundingMetadata"`
}

type GroundingMetadata struct {
	GroundingChunks []GroundingChunk `json:"groundingChunks"`
}

type GroundingChunk struct {
	Web WebContent `json:"web"`
}

type WebContent struct {
	URI   string `json:"uri"`
	Title string `json:"title"`
}

func searchGemini(client *http.Client, apiKey, query string, limit int) ([]SearchResult, error) {
	url := fmt.Sprintf("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=%s", apiKey)

	reqBody := GeminiRequest{
		Contents: []Content{
			{Role: "user", Parts: []Part{{Text: "Search for: " + query}}},
		},
		Tools:            []Tool{{GoogleSearch: map[string]interface{}{}}},
		GenerationConfig: Config{Temperature: 0.0, MaxOutputTokens: 1024},
	}

	body, _ := json.Marshal(reqBody)
	req, _ := http.NewRequest("POST", url, bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")

	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)

	var geminiResp GeminiResponse
	json.Unmarshal(respBody, &geminiResp)

	var results []SearchResult
	for i, chunk := range geminiResp.Candidates[0].GroundingMetadata.GroundingChunks {
		if i >= limit {
			break
		}
		results = append(results, SearchResult{
			Title:   chunk.Web.Title,
			URL:     chunk.Web.URI,
			Snippet: fmt.Sprintf("Source for: %s", query),
		})
	}

	return results, nil
}

func expandQueries(topic string) []string {
	return []string{
		topic,
		topic + " official documentation",
		topic + " github repository",
		topic + " tutorial",
		topic + " architecture",
	}
}

func main() {
	topic := "LLM agents"
	if len(os.Args) > 1 {
		topic = strings.Join(os.Args[1:], " ")
	}

	apiKey := os.Getenv("GEMINI_API_KEY")
	if apiKey == "" {
		fmt.Println("Error: GEMINI_API_KEY not set")
		os.Exit(1)
	}

	fmt.Printf("🔬 Go Research - Topic: %s\n", topic)
	fmt.Println("==========================")

	client := &http.Client{Timeout: 30 * time.Second}

	start := time.Now()

	queries := expandQueries(topic)
	fmt.Printf("Running %d searches...\n", len(queries))

	var wg sync.WaitGroup
	resultsChan := make(chan []SearchResult, len(queries))

	for _, q := range queries {
		wg.Add(1)
		go func(query string) {
			defer wg.Done()
			results, err := searchGemini(client, apiKey, query, 5)
			if err == nil && len(results) > 0 {
				resultsChan <- results
			}
		}(q)
	}

	go func() {
		wg.Wait()
		close(resultsChan)
	}()

	var allResults []SearchResult
	for results := range resultsChan {
		allResults = append(allResults, results...)
	}

	elapsed := time.Since(start)

	fmt.Printf("\nFound %d total results\n", len(allResults))
	fmt.Printf("✓ Research complete in %.1fs\n", elapsed.Seconds())

	if len(allResults) > 0 {
		fmt.Println("\nTop results:")
		for i, r := range allResults[:3] {
			fmt.Printf("%d. %s\n", i+1, r.Title)
			fmt.Printf("   %s\n", r.URL)
		}
	}
}
