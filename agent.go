package main

import (
	"bytes"
	"encoding/json"
	"log"
	"net/http"
	"time"

	"github.com/google/uuid"
)

// Define the payload structure to match what the Flask API expects
type HeartbeatPayload struct {
	AgentID string `json:"agent_id"`
}

const (
	// Change this to your Flask server's actual IP and port
	server 		   = "192.168.0.154"
	port		   = "2766"
	serverURL      = "http://"+host+":"+port+"/api/handshake"
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

	// 2. Send the very first heartbeat immediately upon startup
	sendHeartbeat(client, agentID)

	// 3. Set up a ticker to repeat the handshake every 30 seconds
	ticker := time.NewTicker(reportInterval)
	defer ticker.Stop()

	for range ticker.C {
		sendHeartbeat(client, agentID)
	}
}

func sendHeartbeat(client *http.Client, id string) {
	// Prepare the JSON payload
	payload := HeartbeatPayload{AgentID: id}
	jsonData, err := json.Marshal(payload)
	if err != nil {
		log.Printf("Error formatting JSON: %v\n", err)
		return
	}

	// Create the POST request
	req, err := http.NewRequest("POST", serverURL, bytes.NewBuffer(jsonData))
	if err != nil {
		log.Printf("Error creating request: %v\n", err)
		return
	}
	req.Header.Set("Content-Type", "application/json")

	// Send the request
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