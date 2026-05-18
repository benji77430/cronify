# cronify

easy to intall cron Web interface 

**DASHBOARD**

<img width="3839" height="1834" alt="image" src="https://github.com/user-attachments/assets/9f3bfb47-5535-49e4-804f-31469ead3799" />

**LOGIN PAGE**

<img width="3839" height="1834" alt="image" src="https://github.com/user-attachments/assets/56e5205e-818a-4ba5-ad56-1cf015820236" />

**INSTALLING**

first clone the repository
`git clone https://github.com/benji77430/cronify`
then get into the directory 
`cd cronify`

and install python dependencies
`pip install -r requirements --break-system-packages`

and also install golang if not already done

debian based distros : `apt intall golang`

arch based distros : `pacman -S go`

and finnally run the 2 installers 

the web UI installer for the controller (the main server)
`python3 install.py` (don't forget to run it as root)

and the agent (you can install multiples agent for one web UI to manage every server from one interface :) ) 
`python3 deploy_agent.py` (don't forget to run it as root) 
