import shutil,os,sys,yaml,subprocess

agent_content = r"""package main

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
	AgentName      = "###AGENTNAME###"
	server         = "###AGENTHOST###"
	port           = "###AGENTPORT###"
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
}"""

cronify_agent_service_content = r"""
[Unit]
Description=Cronify Agent
After=multi-user.target

[Service]
Restart=always
User=root
WorkingDirectory=/etc/cronify
ExecStart=/etc/cronify/agent

[Install]
WantedBy=multi-user.target"""

go_mod = r"""module agent

go 1.26.3

require (
	github.com/google/uuid v1.6.0 // indirect
	gopkg.in/yaml.v3 v3.0.1 // indirect
)

"""
go_sum = r"""github.com/google/uuid v1.6.0 h1:NIvaJDMOsjHA8n1jAhLSgzrAzy1Hgr+hNrb57e+94F0=
github.com/google/uuid v1.6.0/go.mod h1:TIyPZe4MgqvfeYDBFedMoGGpEw/LqOeaOT+nhxU+yHo=
gopkg.in/check.v1 v0.0.0-20161208181325-20d25e280405/go.mod h1:Co6ibVJAznAaIkqp8huTwlJQCZ016jof/cbN4VW5Yz0=
gopkg.in/yaml.v3 v3.0.1 h1:fxVm/GzAzEWqLHuvctI91KS9hhNmmWOoWu0XTYJS7CA=
gopkg.in/yaml.v3 v3.0.1/go.mod h1:K4uyk7z7BCEPqu6E+C64Yfv1cQ7kz7rIZviUmN+EgEM=
"""
if shutil.which("go") is None:
    print("please install golang first !")
    exit(1)

if os.getuid != 0:
    print("please run the script as root ! ")

if not os.path.isdir(os.path.join("/etc","cronify")):
    os.makedirs(os.path.join("/etc","cronify"),exist_ok=True)

if not os.path.isfile(os.path.join("/etc","cronify","agent.go")):
    agent_name=input("enter the name of your agent (agent) : ") or "agent"
    agent_host=input("enter the ip or FQDN of your server (127.0.0.1) : ") or "127.0.0.1"
    agent_port=input("enter the port of the webui (2766) : ") or "2766"
    open(os.path.join("/etc","cronify","agent.go"),"w").write(agent_content.replace(r"###AGENTNAME###",agent_name).replace(r"###AGENTHOST###",agent_host).replace(r"###AGENTPORT###",agent_port))
    current_dir=os.path.dirname(os.path.abspath(sys.argv[0]))
    os.chdir(os.path.join("/etc","cronify"))
    open(os.path.join("/etc","cronify","go.mod"),'w').write(go_mod)
    open(os.path.join("/etc","cronify","go.sum"),'w').write(go_sum)
    subprocess.run("go build agent.go",shell=True,check=True)
    os.chdir(current_dir)

    

if not os.path.isfile(os.path.join("/etc","systemd","system","cronify_agent.service")):
    open(os.path.join("/etc","systemd","system","cronify_agent.service"),"w").write(cronify_agent_service_content)
    subprocess.run("systemctl enable cronify_agent.service",shell=True,check=True)
    subprocess.run("systemctl start cronify_agent.service",shell=True,check=True)
