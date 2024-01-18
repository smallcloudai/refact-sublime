# refact-sublime
Refact for VS Code is a free, open-source AI code assistant

#file documentation

__init__.py

Entry point receives key events and update events. It calls refact_sessions methods depending on the event fired. 

refact_sessions.py

On initialization starts the Refact process and gets the connection to the server for LSP calls. 
Sends messages to the LSP object to communicate with the server. 
Holds the session state for each open file. Whenever a new session is created the LSP server is informed about the new file. 
Calls PhantomState which handles displaying the grey text suggestions. 

refact_process.py

Starts the server process and resets the server if it dies. Logs messages from the server and informs the statusbar about server errors. 

refact_lsp.py

Used to communicate directly with the lsp server. 

phantom_state.py

Responsible for displaying the grey text suggestions. 

completion_text.py

Helper functions used by PhantomState to determine the exact text that needs to be displayed. 

utils.py

Helper functions for interacting with the sublime api


Default.sublime-keymap

Used to setup key mappings for suggestion completions. 
Main.sublime-menu
Adds a “pause refact” button to the tools button in the headings.

refact.sublime-settings

Holds the settings for the Refact plugin. 
