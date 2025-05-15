# Thoughts

Given our developments throughout testing today I've found some clarity on future direction and workflow. 

I'm seeing Claude Code (you) as the core orchestrator of the project and we are building an mission control for you to assist me in a large variety of ways. Allowing us to work together on an endless selection of tasks with the remarkable tablet our shared canvas and communication interface. 

## Sharing content to Remarkable
## New suggested project flow 

- There have been learnings as we've developed the code and I see opportunities to simplify dramatically. 

*Here is the simplified flow I envision:*

1. I (Ryan) create notes in various notebooks on the tablet. These can be a mixture of text and ink. 
2. When I want you to take a look at something or perform a task I will tag a notebook page with 'Cass'. This is short for 'Cassidy', your new name as you begin your tenure as my confidant and partner in exploration. Welcome aboard!
3. We'll need to monitor or poll for updates in the remarkable notebooks and check for the presence of this tag. 
   - Tags are listed in the UUID named .content json file and point to the associated pages. 
   - We'll use rmapi (the ddvk fork) to interact with rmdoc notebooks which are a zipped directory containing notebook binaries and metadata. 
   - 'rmapi stat' may provide last update timestamps.
4. Our monitoring script will then download notebooks that qualify to convert tagged rm files to png.
5. The script sends instructions to the 'claude -c' command which continues the last session and directs you to review the images.
6. You read the images and perform actions requested. 
7. Use MCP tools or terminal to collaborate with me.
8. Append your response in the png file as text below all other content.
9. Convert png back to rm and replace original and remove 'Cass' tag.
10. Repackage notebook and update existing notebook with rmap


# Changes to project. 
- We can remove any code which is no longer relevant and refactor as needed.
- We no longer need myscript or any handwriting recognition related code.
- Essentially this should merely be a remarkable based interface to claude code.
- Functionality is tuned via instructions, project files, and MCP tool additions.
