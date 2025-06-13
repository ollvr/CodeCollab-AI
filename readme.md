# CodeCollab AI - README

Welcome to CodeCollab AI, a collaborative coding assistant application designed to enhance your programming experience by leveraging multiple AI models. This README will guide you through setting up, using, and customizing CodeCollab AI to suit your needs.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Customization](#customization)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features

CodeCollab AI offers a range of features to assist you in your coding tasks:

- **Multi-AI Collaboration**: Utilize multiple AI models simultaneously to get comprehensive assistance.
- **Conversation Management**: Easily manage and switch between different coding conversations.
- **Export Functionality**: Save your conversations for future reference or sharing.
- **Customizable AI Models**: Tailor the AI models to better fit your specific needs.

## Prerequisites

Before you begin, ensure you have the following installed:

- Ollama installed
- Python version >= 3.9
- `langchain_ollama` package

## Installation

To get started with CodeCollab AI, follow these steps:

1. **Clone the Repository**:
   ```bash
   git clone <https://github.com/ollvr/CodeCollab-AI.git>
   cd <CodeCollabAI>
   ```

2. **Install Dependencies**:
   ```bash
   pip install langchain_ollama
   ```

3. **Run the Application**:
   ```bash
   python app.py
   ```

## Usage

### Starting the Application

Launch the application using the command provided in the installation section. The application window will open, ready for you to start interacting with the AI.

### Using the Application

1. **Select AI Models**: Choose the AI models that best suit your needs from the available options.

2. **Start a New Conversation**:
   - Begin a new chat session to discuss your coding queries.
   - Provide a name for your conversation when prompted to keep your sessions organized.

3. **Interact with the AI**:
   - Type your questions or coding problems to receive assistance.
   - The AI will respond with suggestions, code snippets, or explanations based on your input.

4. **Manage Conversations**:
   - Easily switch between different conversations to keep your work organized.
   - Delete old conversations that are no longer needed.

5. **Export a Conversation**:
   - Save your conversation history to a text file for future reference or documentation.

## Customization

### Changing AI Models

You can customize the AI models used by modifying the `get_available_models` function in the code. This allows you to add or remove models based on your preferences or requirements.

### Customizing the Application

The application can be customized further by modifying the code to change behaviors, add new features, or adjust existing ones to better fit your workflow.

## Troubleshooting

If you encounter any issues while using CodeCollab AI, here are some common troubleshooting steps:

- **Module Import Errors**: Ensure all dependencies are correctly installed. If you encounter import errors, verify the installation steps.
- **Application Not Starting**: Check that you have the correct version of Python and that all necessary libraries are installed.
- **Conversation Issues**: Ensure that the application has the necessary permissions to read and write files, especially in the `conversations` directory.

## Contributing

We welcome contributions to CodeCollab AI! If you have suggestions for improvements or new features, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Commit your changes with clear, descriptive messages.
4. Push your changes to your fork.
5. Submit a pull request with a detailed description of your changes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.

---

Thank you for using CodeCollab AI! We hope this application enhances your coding experience and makes your development process more efficient and enjoyable. If you have any questions or feedback, please don't hesitate to reach out.