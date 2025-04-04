### CodeCollab AI: Collaborative LLM Coding Assistant
Where multiple large language models team up to solve your programming problems.

## Introduction
CodeCollab AI is an innovative coding assistant that simulates a collaborative environment where multiple large language models (LLMs) work together to solve programming problems. Inspired by the dynamics of a developer chatroom, the app allows users to interact with a main LLM that can call upon two helper LLMs for assistance when needed. This collaborative approach aims to provide more accurate and helpful responses to programming queries.

## Features
Collaborative LLMs: A main LLM and two helper LLMs collaborate to solve problems.
Conversation Management: Create, load, and delete conversations, each saved as a JSON file.
User Feedback Loop: Provide feedback on responses to improve future answers.
Model Selection: Choose from various LLMs for the main and helper roles.
Token Management: Ensures prompts fit within the model's context window.
Intuitive GUI: User-friendly interface for seamless interaction.


## How to Use
Install Ollama: Download and install Ollama from ollama.ai to run LLMs locally.
Pull Required Models: Use Ollama to pull the models you want to use. For example

ollama run deepseek-coder-v2
ollama run qwen2.5-coder:latest
ollama ollama run deepseek-r1

Run the App: Execute the Python script (e.g., python app.py) to launch the GUI.

Select Models: Choose models for the main developer and helpers from the dropdown menus in the left sidebar.

As an example, the app includes deepseek-coder-v2, qwen2.5-coder:latest, and deepseek-r1:8b, but you can customize these by modifying the get_available_models() function in the code

Pay attention to change also the model context window with the correct values .

def get_available_models():
    return ["deepseek-coder-v2", "qwen2.5-coder:latest", "deepseek-r1:8b"] # replace with the llms you wants


Start a New Chat: Click "New Chat," name your conversation, and begin interacting.

Interact with the LLMs:

Type your programming question or request in the input field and press "Send" or hit Enter.
The main LLM will respond.

You’ll be asked if the response was helpful (type "yes" or "no").

If "yes," the conversation continues or ends based on your next input.
If "no," optionally provide feedback (or press Enter to skip), and the main LLM will consult the helpers to improve its response.

Manage Conversations: Load or delete existing conversations from the sidebar.    

## Dependencies
To run CodeCollab AI, ensure you have the following installed:

Python 3.x: The app is written in Python.
Tkinter: Used for the GUI; typically included with Python, but ensure it’s available on your system.
Langchain Community: Install via pip:

pip install langchain-community

Ollama: Required to run LLMs locally. Install from ollama.ai.

Additionally, pull the necessary models in Ollama (e.g., deepseek-coder-v2, qwen2.5-coder,deepseek-r1) to ensure the app functions correctly. 

You can customize the available models by editing the get_available_models() function in the code as described above.


## Upcoming Features
Chatroom with PDF Support: Future versions will allow LLMs to collaborate on answering questions about PDF documents uploaded by the user.

Interpreter Integration: Plans to add an interpreter for executing and testing code snippets directly within the app.


## Notes
Performance: Response times may vary depending on your hardware.

Contributing: If you enjoy using CodeCollab AI, consider starring the project on GitHub! 

We welcome contributions and feedback to make the app even better.