package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"github.com/google/uuid"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"time"
)

// Define the payload structure to match what the Flask API expects
type HeartbeatPayload struct {
	AgentID   string `json:"agent_id"`
	AgentName string `json:"agent_name"`
}
type APIResponse struct {
	Jobs []CronJob `json:"jobs"`
}
type CronJob struct {
	ID      int    `json:"id"`
	Minute  string `json:"minute"`
	Hour    string `json:"hour"`
	Day     string `json:"day"`
	Month   string `json:"month"`
	Weekday string `json:"weekday"`
	User    string `json:"user"`
	Command string `json:"command"`
}

const (
	AgentName      = "Server"
	server         = "192.168.0.154"
	port           = "2766"
	serverURL      = "http://" + server + ":" + port + "/api/handshake"
	reportInterval = 30 * time.Second
)

func main() {
	// 1. Generate a unique ID for this agent instance
	agentID := uuid.New().String()
	log.Printf("Agent started successfully. Unique ID: %s\n", agentID)

	// Create an HTTP client with a 5-second timeout so it doesn't hang forever
	client := &http.Client{
		Timeout: 5 * time.Second,
	}

	// 2. Send the very first heartbeat and cron check immediately upon startup
	sendHeartbeat(client, agentID, AgentName)
	updatecron()

	// 3. Set up tickers
	heartbeatTicker := time.NewTicker(reportInterval)
	cronTicker := time.NewTicker(reportInterval * 2)
	defer heartbeatTicker.Stop()
	defer cronTicker.Stop()

	// FIX: Use a select block inside a single loop, or run them in goroutines.
	// Otherwise, the first for loop blocks the second one from ever starting!
	for {
		select {
		case <-heartbeatTicker.C:
			sendHeartbeat(client, agentID, AgentName)
		case <-cronTicker.C:
			updatecron()
		}
	}
}

func sendHeartbeat(client *http.Client, id string, AgentName string) {
	payload := HeartbeatPayload{AgentID: id, AgentName: AgentName}
	jsonData, err := json.Marshal(payload)
	if err != nil {
		log.Printf("Error formatting JSON: %v\n", err)
		return
	}

	req, err := http.NewRequest("POST", serverURL, bytes.NewBuffer(jsonData))
	if err != nil {
		log.Printf("Error creating request: %v\n", err)
		return
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := client.Do(req)
	if err != nil {
		log.Printf("Server unreachable: %v\n", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusOK {
		log.Println("Heartbeat sent successfully (200 OK).")
	} else {
		log.Printf("Server responded with unexpected status: %s\n", resp.Status)
	}
}

func updatecron() {
	resp, err := http.Get("http://" + server + ":" + port + "/api/cron")
	if err != nil {
		log.Printf("Server unreachable: %v\n", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		log.Printf("Server returned bad status: %s\n", resp.Status)
		return
	}

	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Printf("Failed to read response body: %v\n", err)
		return
	}

	var statusCheck map[string]string
	json.Unmarshal(bodyBytes, &statusCheck)

	if statusCheck["status"] == "error" {
		log.Printf("API Notification: %s (No actions taken)\n", statusCheck["message"])
		return
	}

	var apiData APIResponse
	err = json.Unmarshal(bodyBytes, &apiData)
	if err != nil {
		log.Printf("Failed to parse JSON jobs list: %v\n", err)
		return
	}

	log.Printf("Successfully parsed %d cron jobs.\n", len(apiData.Jobs))

	var cronLines []string
	for _, job := range apiData.Jobs {
		line := fmt.Sprintf("%s %s %s %s %s %s %s",
			job.Minute, job.Hour, job.Day, job.Month, job.Weekday, job.User, job.Command)
		cronLines = append(cronLines, line)
	}

	cronContent := strings.Join(cronLines, "\n") + "\n"

	tmpPath := "/etc/cron.d/cronify.tmp"
	finalPath := "/etc/cron.d/cronify"

	// FIX 1: Convert string to []byte using []byte(cronContent)
	// FIX 2: Log the errors instead of trying to return them out of a void function
	if err := os.WriteFile(tmpPath, []byte(cronContent), 0644); err != nil {
		log.Printf("Failed to write temp file: %v\n", err)
		return
	}

	if err := os.Chown(tmpPath, 0, 0); err != nil {
		log.Printf("Failed to chown temp file to root: %v\n", err)
		return
	}

	if err := os.Rename(tmpPath, finalPath); err != nil {
		log.Printf("Failed to atomically replace cronify file: %v\n", err)
		return
	}

	log.Println("Successfully updated /etc/cron.d/cronify atomically.")
}