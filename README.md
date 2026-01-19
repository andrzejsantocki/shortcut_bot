# Shortcuts Mini App

A desktop application for managing and viewing keyboard shortcuts, powered by an AI agent that helps structure and categorize your commands.

## Features

- **Shortcut Viewer:** A clean and simple GUI to browse your shortcuts by application.
- **AI-Powered Agent:** Use natural language to add new shortcuts. The AI agent will automatically categorize, generalize, and describe them for you.
- **Cloud Sync:** Your shortcuts are synced with a cloud-based JSON store (jsonbin.io), so you can use them across multiple devices.
- **Global Hotkey:** A global hotkey (`<ctrl>+<shift>+h`) allows you to quickly show or hide the application.
- **Safe and Secure:** The application uses a lock file to prevent multiple instances from running at the same time, and it includes safety checks to prevent data loss.

## How it Works

The application is composed of several key components:

- **`shortcuts_app.pyw`:** The main GUI application, built with Tkinter. It displays a list of applications and their corresponding shortcuts.
- **`agent.py`:** A command-line tool that uses the OpenAI API (GPT-4o) to process natural language commands and transform them into structured JSON objects. It has three modes: `watch`, `process`, and `manual`.
- **`shortcuts.json`:** A local JSON file that stores all your shortcuts.
- **`sync_cloud_to_local.py` and `sync_local_to_cloud.py`:** These scripts handle the synchronization of your shortcuts between your local `shortcuts.json` file and the cloud (jsonbin.io).
- **`file_utils.py` and `json_validator.py`:** Utility scripts for file operations and JSON validation.

## Getting Started

### Prerequisites

- Python 3.x
- An OpenAI API key
- A jsonbin.io account

### Installation

1.  Clone this repository:
    ```bash
    git clone https://github.com/your-username/shortcuts-mini-app.git
    ```
2.  Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: A `requirements.txt` file is not included in the project. You will need to create one based on the imports in the Python files.)*

3.  Create a `.env` file in the root directory and add the following:
    ```
    OPENAI_API_KEY=your-openai-api-key
    BIN_URL=your-jsonbin-io-bin-url
    MASTER_KEY=your-jsonbin-io-master-key
    ```

### Usage

1.  Run the application:
    ```bash
    python shortcuts_app.pyw
    ```
2.  The application will start in the background. Use the global hotkey (`<ctrl>+<shift>+h`) to show or hide the window.
3.  To add a new shortcut, click the "Agent" button. This will open a terminal where you can enter a command in natural language. The AI agent will then guide you through the process of adding the new shortcut.

## Future Development

- **Local LLM Integration:** The `langchain_utils.py` file contains a template for integrating a local Large Language Model (LLM) using the LangChain framework. This would allow the application to run without an internet connection and without relying on the OpenAI API.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
