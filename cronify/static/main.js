async function getAgents() {
    const response = await fetch("/api/agents");
    const count = await response.text();
    
    const agentsElement = document.getElementById("agents");
    if (agentsElement) {
        agentsElement.innerText = "connected agents : " + count;
    }
    setTimeout(getAgents, 5000);
}
getAgents();

function toggle(mode) {
    const element = document.getElementById("cronify-form");
    element.style.visibility = mode;
       
}

function deleteJob(jobId) {
    // 1. Define the endpoint URL
    const url = '/delete'; 
    console.log("deleting job : "+jobId);
    // 2. Define the payload
    const data = { id: jobId };

    // 3. Fire the fetch request
    fetch(url, {
        method: 'POST', // Specify the HTTP method
        headers: {
            'Content-Type': 'application/json' // Tell the server you're sending JSON
        },
        body: JSON.stringify(data) // Turn your JS object into a text string
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json(); // Parse the server's response JSON
    })
    .then(result => {
        console.log('Success:', result);
        // Refresh the page or update the UI here
        window.location.reload(); 
    })
    .catch(error => {
        console.error('Error sending POST request:', error);
    });
}