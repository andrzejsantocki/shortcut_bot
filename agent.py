import json
import logging
import os
import re
import subprocess
import sys
import time
from copy import deepcopy

import click
import requests
from colorama import Fore, Style, init
from dotenv import load_dotenv

# This import assumes you have a 'file_utils.py' with the required functions.
from file_utils import update_shortcuts_safely

# Initialize colorama for colored terminal output
init(autoreset=True)

# Configure logging to ONLY write to the file.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent.log"),
    ]
)

load_dotenv()

# --- Configuration Constants ---
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    log_msg = "CRITICAL ERROR: OPENAI_API_KEY not found in .env file. Please add it."
    logging.critical(log_msg)
    click.echo(Fore.RED + log_msg)
    sys.exit(1)

MODEL_NAME = "gpt-4o"
SHORTCUTS_FILE = "shortcuts.json"
NEW_COMMAND_FILE = "new_command.txt"


def print_colored_json(payload, crucial_keys=None):
    """
    Prints a JSON payload to the console with robust syntax highlighting.
    This version iterates line-by-line to avoid complex regex failures.

    Args:
        payload (dict): The Python dictionary to format and print.
        crucial_keys (list, optional): A list of keys to highlight in orange.
    """
    if crucial_keys is None:
        crucial_keys = []

    json_str = json.dumps(payload, indent=2)
    colored_lines = []

    for line in json_str.splitlines():
        match = re.match(r'(\s*)(".*?")(: )?(.*)', line)
        if match:
            indent, key, colon, rest = match.groups()
            
            # This is a key-value line
            if colon:
                # Check if the key (without quotes) is crucial
                if key.strip('"') in crucial_keys:
                    key_color = Fore.YELLOW  # Orange/Yellow for crucial keys
                else:
                    key_color = Fore.CYAN    # Cyan for standard keys
                
                # Colorize the value based on its type
                if rest.startswith('"'):
                    value_color = Fore.GREEN
                elif rest in ['true,', 'false,', 'true', 'false']:
                    value_color = Fore.MAGENTA
                elif rest in ['null,', 'null']:
                    value_color = Fore.RED
                else: # It's a number
                    value_color = Fore.YELLOW
                
                colored_line = f"{indent}{key_color}{key}{Style.RESET_ALL}{colon}{value_color}{rest}{Style.RESET_ALL}"
                colored_lines.append(colored_line)
            else:
                 # This is a line with a single value (e.g., in a list)
                colored_lines.append(f"{indent}{Fore.GREEN}{key}{Style.RESET_ALL}")
        else:
            colored_lines.append(line) # Fallback for lines without keys (e.g., '{', '}')

    click.echo("\n".join(colored_lines))


def sync_cloud_on_startup():
    """Executes the cloud-to-local sync script at startup."""
    logging.info("Syncing cloud with local on startup...")
    subprocess.run(["python", "sync_cloud_to_local.py"])


def format_command_with_llm(raw_command):
    """
    Formats a raw command string into a structured JSON object using the OpenAI LLM.
    Logs the full request/response to file and prints a colorized, compact
    version to the terminal.

    Args:
        raw_command (str): The raw command input by the user.

    Returns:
        str: A JSON string of the formatted command, or None if an error occurs.
    """
    logging.info("Reading shortcuts file for context...")
    with open(SHORTCUTS_FILE, 'r') as f:
        shortcuts_data = json.load(f)

    existing_categories = list(shortcuts_data.keys())
    
    
    
    prompt = f'''
            You are an expert assistant specializing in command-line tools. Your task is to analyze a raw user command, derive a generalized template from it, and format the output into a structured JSON object.

            ---
            **CONTEXT AND EXAMPLES**

            Here are some examples of the desired transformation:

            **Example 1:**
                - **Raw User Command:** "add to gitignore !wip_scripts/ !wip_scirpts/* to see all files in git"
            - **Expected JSON Output:**
              ```json
              {{
                "category": "Git",
                "command": "!folder_name/\\n!folder_name/*",
                "description": "Excludes a specific folder and its contents from Git tracking, which is useful for ignoring temporary or local files.",
                "usage example": "!wip_scripts/\\n!wip_scripts/*"
              }}
            Example 2:
            Raw User Command: "git checkout -b new_feature_branch to start working on a new feature"
            Expected JSON Output:
            code
            JSON
            {{
              "category": "Git",
              "command": "git checkout -b <branch_name>",
              "description": "Creates a new branch and immediately switches to it, allowing for isolated development of a new feature.",
              "usage example": "git checkout -b new_feature_branch"
            }}
            
            YOUR TASK
            Raw command provided by the user: "{raw_command}"
            Existing Categories for Reference:
            {json.dumps(existing_categories, indent=2)}
            Full Context of Existing Shortcuts for Reference:
            {json.dumps(shortcuts_data, indent=2)}
            Instructions:
            Please analyze the raw command and generate a single JSON object by following these steps:
            Categorize: Determine the most appropriate category. Prioritize using an existing category if it's a good fit. If not, suggest a concise new category.Format all categories in uppercase.
            Generalize the Command: Create a generalized, symbolic command template. Replace specific names (like filenames, folder names, branch names, URLs) with generic placeholders (e.g., <branch_name>, folder_name/*, <file_extension>). This will be the value for the "command" key.
            Define the Usage: The specific user command goes here. Correct any obvious typos from the raw command (e.g., 'restor' becomes 'restore'). This will be the value for the "usage example" key. You are prohibited to add command description here.
            Describe the Purpose: Write a clear, one-sentence description that explains what problem the command mitigates or what purpose it serves.
            Output Format:
            Format the output as a single JSON object with the following keys. Do not include any surrounding text or code blocks.
            "category": (The chosen or new category name)
            "command": (The generalized, symbolic command template, NOT the raw command)
            "description": (The explanation of the command's purpose and the problem it solves)
            "usage example": (The specific, corrected user command)
            ''' 





    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    
    # This is the actual data payload sent in the request
    data = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are an expert assistant that analyzes raw user commands and transforms them into a structured JSON object with three fields: 'Command', 'Usage', and 'Description'. Your primary task is to create a generalized, symbolic rule for the 'Command' field, not just copy the user's input. The 'Usage' field should contain the user's specific command, and the 'Description' should explain the purpose of the command."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5,
    }

    # Create a modified copy of the payload for a more readable terminal display
    display_data = deepcopy(data)
    original_prompt = display_data["messages"][1]["content"]
    # Condense the massive prompt into a single truncated line
    compact_prompt = ' '.join(original_prompt.split())
    display_data["messages"][1]["content"] = f"{compact_prompt[:150]}..."

    # Log the full request to file and print the compact, colorized version to terminal
    title = "--- OpenAI Request Payload ---"
    logging.info(f"{title}\n{json.dumps(data, indent=2)}")
    click.echo(Style.BRIGHT + title)
    print_colored_json(display_data, crucial_keys=["model", "role", "content"])

    logging.info(f"Sending POST request to: {OPENAI_API_URL}...")
    try:
        response = requests.post(OPENAI_API_URL, headers=headers, json=data)
        response.raise_for_status()
        response_json = response.json()

        # Log the full response to file and print the colorized version to terminal
        title = "--- OpenAI Response Payload ---"
        logging.info(f"{title}\n{json.dumps(response_json, indent=2)}")
        click.echo(Style.BRIGHT + title)
        print_colored_json(response_json, crucial_keys=["model", "finish_reason", "content"])

        response_content = response_json["choices"][0]["message"]["content"]
        logging.info("Received successful response from API.")
        return response_content

    except requests.exceptions.HTTPError as http_err:
        log_msg = f"HTTP error occurred: {http_err}"
        logging.error(log_msg)
        logging.error(f"Response body: {response.text}")
        click.echo(Fore.RED + log_msg)
        return None
    except Exception as e:
        log_msg = f"An unexpected error occurred: {e}"
        logging.error(log_msg)
        click.echo(Fore.RED + log_msg)
        return None


def _process_command_logic(raw_command):


    """


    Shared logic to process a raw command string.


    Takes a raw command, formats it, validates it, gets user approval,


    and updates the shortcuts file.


    """


    if not raw_command:


        logging.info("No command provided to process.")


        click.echo(Fore.YELLOW + "No command provided to process.")


        return





    click.echo(Fore.CYAN + f"New command detected: {raw_command}")
    formatted_command_str = format_command_with_llm(raw_command)





    if formatted_command_str is None:
        logging.error("Failed to get formatted command from API. Aborting.")
        click.echo(Fore.RED + "ERROR: Failed to get formatted command from API. Aborting.")
        return





    logging.info("Formatted command received from LLM.")
    try:
        if formatted_command_str.strip().startswith("```json"):
            formatted_command_str = formatted_command_str.strip()[7:-3].strip()
        formatted_command = json.loads(formatted_command_str)
        logging.info("Successfully parsed JSON from LLM response.")
        click.echo(Fore.GREEN + "✓ LLM response is valid JSON.")


    except json.JSONDecodeError:


        log_msg = f"LLM did not return valid JSON. Response was:\n{formatted_command_str}"
        logging.error(log_msg)
        click.echo(Fore.RED + f"✗ ERROR: LLM did not return valid JSON. Response was:\n{formatted_command_str}")
        return





    with open(SHORTCUTS_FILE, 'r') as f:


        shortcuts = json.load(f)





    category = formatted_command.get("category")


    if not category:


        log_msg = "LLM response did not include a 'category'. Aborting."


        logging.error(log_msg)


        click.echo(Fore.RED + f"✗ ERROR: {log_msg}")


        return


    click.echo(Fore.GREEN + "✓ 'category' key found in LLM response.")





    if category not in shortcuts:


        logging.warning(f"Category '{category}' does not exist.")


        if not click.confirm(Fore.YELLOW + f"Category '{category}' does not exist. Do you want to create it?"):


            logging.warning("User chose not to create a new category. Aborting.")


            click.echo(Fore.YELLOW + "Aborted by user.")


            return


        logging.info(f"User approved creation of new category: {category}")


        shortcuts[category] = []





    proposed_command_text = formatted_command.get("command")


    if category in shortcuts:


        for existing_command in shortcuts[category]:


            if existing_command.get("command") == proposed_command_text:


                log_msg = f"Duplicate command found in category '{category}'. Aborting."


                logging.warning(log_msg)


                click.echo(Fore.YELLOW + f"✗ This command already exists in the '{category}' category. Aborting.")


                return


    click.echo(Fore.GREEN + "✓ Command is not a duplicate.")





    click.echo(Fore.CYAN + "\nProposed command to add:")


    click.echo(Style.BRIGHT + json.dumps(formatted_command, indent=2))





    if not click.confirm(Fore.GREEN + "\nDo you approve this command?"):


        logging.warning("Command not approved by user. Aborting.")


        click.echo(Fore.YELLOW + "Command not approved. Aborting.")


        return





    logging.info("User approved command. Proceeding to update shortcuts.")





    # Get pre-update line count


    try:


        with open(SHORTCUTS_FILE, 'r') as f:


            lines_before = len(f.readlines())


    except FileNotFoundError:


        lines_before = 0





    command_to_add = {k: v for k, v in formatted_command.items() if k != "category"}


    shortcuts[category].append(command_to_add)


    updated_content = json.dumps(shortcuts, indent=2)





    if not update_shortcuts_safely(SHORTCUTS_FILE, updated_content):


        log_msg = "Failed to update shortcuts.json safely. Aborting."


        logging.error(log_msg)


        click.echo(Fore.RED + f"ERROR: {log_msg}")


        return





    # Get post-update line count and report difference


    with open(SHORTCUTS_FILE, 'r') as f:


        lines_after = len(f.readlines())


    line_diff = lines_after - lines_before





    validation_result = subprocess.run(


        ["python", "json_validator.py", SHORTCUTS_FILE],


        capture_output=True, text=True


    )


    if "True" not in validation_result.stdout:


        logging.error("shortcuts.json validation failed. Aborting.")


        logging.error(f"Validator output: {validation_result.stdout}")


        click.echo(Fore.RED + "✗ ERROR: shortcuts.json validation failed. Aborting.")


        return





    click.echo(Fore.GREEN + f"Successfully updated shortcuts.json ({('+' if line_diff >= 0 else '')}{line_diff} lines).")


    click.echo(Fore.GREEN + "✓ shortcuts.json passed validation.")


    logging.info("JSON validation successful.")





    subprocess.run(["python", "sync_local_to_cloud.py"])


    logging.info("Successfully synced to the cloud.")










def process_new_command():


    """


    The main workflow for processing a command from the NEW_COMMAND_FILE.


    """
    logging.info("Processing new command from file...")


    with open(NEW_COMMAND_FILE, 'r') as f:
        raw_command = f.read().strip()


    _process_command_logic(raw_command)
    with open(NEW_COMMAND_FILE, 'w') as f:
        f.write("")

    logging.info("Cleared new_command.txt.")








def watch_for_new_command():

    """Monitors new_command.txt for changes and triggers the processing workflow."""

    log_msg = f"Watching for new commands in '{NEW_COMMAND_FILE}'..."
    logging.info(log_msg)
    click.echo(Fore.CYAN + log_msg)


    try:


        last_modified = os.path.getmtime(NEW_COMMAND_FILE)


    except FileNotFoundError:


        log_msg = f"{NEW_COMMAND_FILE} not found. Please create it."


        logging.error(log_msg)


        click.echo(Fore.RED + f"ERROR: {log_msg} and restart.")


        return





    while True:


        time.sleep(2)


        try:


            current_modified = os.path.getmtime(NEW_COMMAND_FILE)


            if current_modified != last_modified:


                last_modified = current_modified


                process_new_command()


        except FileNotFoundError:


            log_msg = f"{NEW_COMMAND_FILE} was deleted. Stopping watch."
            logging.warning(log_msg)
            click.echo(Fore.YELLOW + f"WARNING: {log_msg}")
            break








@click.group()

def cli():
    """A CLI tool to manage and process command shortcuts."""
    pass





@cli.command()

def watch():
    """Monitors new_command.txt for changes and processes them continuously."""
    click.echo(Fore.GREEN + "Starting agent in watch mode...")
    sync_cloud_on_startup()
    watch_for_new_command()








@cli.command()


def process():


    """Processes the current command in new_command.txt immediately."""
    click.echo(Fore.GREEN + "Starting a one-time processing of new command...")
    sync_cloud_on_startup()
    process_new_command()
    click.echo(Fore.GREEN + "Processing finished.")








@cli.command()
def manual():

    """Processes a command entered manually in the terminal."""
    click.echo(Fore.GREEN + "Starting manual command processing...")
    sync_cloud_on_startup()
    raw_command = click.prompt(Fore.CYAN + "Please enter the command to process")
    _process_command_logic(raw_command)
    click.echo(Fore.GREEN + "Manual processing finished.")








if __name__ == "__main__":
    cli()

