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