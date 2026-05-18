import shutil,os,sys,yaml,subprocess

agent_content = r"""package main

import (
	"bytes"
	"encoding/json"
	"log"
	"net/http"
	"time"
	"io"
	"fmt"
	"os"
	"strings"
	"github.com/google/uuid"
)

// Define the payload structure to match what the Flask API expects
type HeartbeatPayload struct {
	AgentID string `json:"agent_id"`
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
	Command string `json:"command"`
}
const (
	// Change this to your Flask server's actual IP and port
	AgentName	   = "###AGENTNAME###"
	server 		   = "###AGENTHOST###"
	port		   = "###AGENTPORT###"
	serverURL      = "http://"+server+":"+port+"/api/handshake"
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
	sendHeartbeat(client, agentID,AgentName)
	updatecron()

	// 3. Set up a ticker to repeat the handshake every 30 seconds
	ticker := time.NewTicker(reportInterval)
	defer ticker.Stop()

	for range ticker.C {
		sendHeartbeat(client, agentID,AgentName)
	}
	ticker_updatecron := time.NewTicker(reportInterval*2)
	defer ticker_updatecron.Stop()

	for range ticker_updatecron.C {
		//run update cron job 
		updatecron()
	}
}

func sendHeartbeat(client *http.Client, id string, AgentName string) {
	// Prepare the JSON payload
	payload := HeartbeatPayload{AgentID: id,AgentName: AgentName}
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

func updatecron() {
	resp,err := http.Get("http://"+server+":"+port+"/api/cron")
	log.Println(resp)
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

	// 2. Check if the API explicitly sent back an error status
	if statusCheck["status"] == "error" {
		log.Printf("API Notification: %s (No actions taken)\n", statusCheck["message"])
		
		// Optional: Clear out /etc/cron if you want it empty when there are no jobs
		// os.WriteFile("/etc/cron", []byte(""), 0644)
		
		return // Exit early since there are no jobs to loop through!
	}

	// 3. If it wasn't an error, carry on parsing your jobs wrapper safely!
	var apiData APIResponse
	err = json.Unmarshal(bodyBytes, &apiData)
	if err != nil {
		log.Printf("Failed to parse JSON jobs list: %v\n", err)
		return
	}

	// 4. Now this loop is 100% safe from crashing when the DB is empty
	log.Printf("Successfully parsed %d cron jobs.\n", len(apiData.Jobs))
	for _, job := range apiData.Jobs {
		log.Printf("Command to write: %s", job.Command)
	}
	// 1. Create a slice of strings to hold each formatted crontab line
	var cronLines []string

	// 2. Loop through every job and format it into a string line
	for _, job := range apiData.Jobs {
		// Formats exactly to: "minute hour day month weekday command"
		line := fmt.Sprintf("%s %s %s %s %s %s", 
			job.Minute, job.Hour, job.Day, job.Month, job.Weekday, job.Command)
		
		cronLines = append(cronLines, line) // Add the line to our collection
	}

	// 3. Join all individual cron lines together with line breaks
	// Also add a final trailing newline (\n) at the very end so Linux cron reads it properly
	cronContent := strings.Join(cronLines, "\n") + "\n"

	// 4. Convert the string to raw bytes and write it straight to /etc/cron
	cronFilePath := "/etc/crontab"
	err = os.WriteFile(cronFilePath, []byte(cronContent), 0644)
	if err != nil {
		log.Printf("Failed to write crontabs to %s: %v (Are you running with sudo?)\n", cronFilePath, err)
		return
	}
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

if not os.path.isfile(os.path.join("/etc","cron.d","cronify")):
    subprocess.run("chown root:root /etc/cron.d/cronify",shell=True,check=True)
    subprocess.run("chmod 644 /etc/cron.d/cronify",shell=True,check=True)
    

if not os.path.isfile(os.path.join("/etc","systemd","system","cronify_agent.service")):
    open(os.path.join("/etc","systemd","system","cronify_agent.service"),"w").write(cronify_agent_service_content)
    subprocess.run("systemctl enable cronify_agent.service",shell=True,check=True)
    subprocess.run("systemctl start cronify_agent.service",shell=True,check=True)
