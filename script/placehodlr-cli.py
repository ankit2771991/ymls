#!/usr/bin/env python3

import argparse
import openai
import os
import pymongo
import re
import subprocess
import sys
from pathlib import Path

# Fetch OpenAI, MongoDB credentials, and model key from environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
MONGODB_URI = os.getenv('MONGODB_URI')
OPENAI_MODEL_KEY = os.getenv('OPENAI_MODEL_KEY')

# Check if OpenAI API key is available
if not OPENAI_API_KEY:
  print("Error: OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
  sys.exit(1)

# Check if MongoDB URI is available
if not MONGODB_URI:
  print("Error: MongoDB URI not found. Please set the MONGODB_URI environment variable.")
  sys.exit(1)

# Check if OpenAI model key is available
if not OPENAI_MODEL_KEY:
  print("Error: OpenAI model key not found. Please set the OPENAI_MODEL_KEY environment variable.")
  sys.exit(1)

# OpenAI and MongoDB Setup
openai.api_key = OPENAI_API_KEY

# MongoDB setup using the URI from environment variable
client = pymongo.MongoClient(MONGODB_URI)
db = client["ansible_logs"]
collection = db["playbook_url"]

LOG_FILE = Path.home() / 'command_log.csv'
STATE_FILE = Path.home() / '.placehodlr_state'

def ask_chatgpt(messages):
  try:
    response = openai.ChatCompletion.create(
      model=OPENAI_MODEL_KEY,  # Model key is now fetched from the environment
      messages=messages
    )
    return response.choices[0].message['content'].strip()
  except openai.error.OpenAIError as e:
    print(f"Error while calling OpenAI API: {e}")
    sys.exit(1)

def extract_filename_from_response(response):
  """
  Extract the filename from the model response.
  """
  filename_pattern = r"\'(.*?)\'"
  filenames = re.findall(filename_pattern, response)
  return filenames[0] if filenames else None

def fuzzy_search_filepath(filename):
  """
  Perform a fuzzy search on filePath in StackOverflowPromptSchema.
  Replace underscores with spaces in both the filename and filePath before searching.
  """
  sanitized_filename = filename.replace("_", " ")

  pipeline = [
    {
      "$search": {
        "index": "default",
        "text": {
          "query": sanitized_filename,
          "path": "adapterInfo.chatGptAdapter.filePath",
          "fuzzy": {
            "maxEdits": 2,
            "prefixLength": 3
          }
        }
      }
    },
    {"$limit": 1}
  ]

  result = db["stackoverflow_prompts_new"].aggregate(pipeline)
  result = list(result)

  return result[0] if result else None

def download_file(url, output_filename):
  try:
    result = subprocess.run(['wget', '--no-check-certificate', url, '-O', output_filename], check=True)
    print(f"File downloaded: {output_filename}")
  except subprocess.CalledProcessError as e:
    print(f"Error downloading file: {e}")
    sys.exit(1)

def run_ansible_playbook(playbook_file, extra_vars):
  command = ['ansible-playbook', playbook_file]

  if extra_vars:
    # Append the formatted extra_vars
    command.append('--extra-vars')
    command.append(extra_vars)

  # Print the command before execution
  print(f"Running Ansible command: {' '.join(command)}")

  try:
    result = subprocess.run(command, check=True)
    print(f"Ansible playbook {playbook_file} executed successfully.")
  except subprocess.CalledProcessError as e:
    print(f"Error running Ansible playbook: {e}")
    sys.exit(1)


def prompt_for_extra_vars(extra_vars):
  """
  Prompt the user to provide values for each extra variable.
  """
  user_vars = {}
  for key, default_value in extra_vars.items():
    user_input = input(f"Provide a value for '{key}' (default: {default_value}): ")
    user_vars[key] = user_input if user_input else default_value
  return user_vars


def format_extra_vars(extra_vars):
  """
  Format the extra variables as a JSON-like string for the Ansible playbook.
  """
  return " ".join([f"{key}={value}" for key, value in extra_vars.items()])

def main():
  parser = argparse.ArgumentParser(
    description="Placehodlr FT CLI to interact with ChatGPT and deploy Ansible playbooks.")
  subparsers = parser.add_subparsers(dest='command', required=True)

  # Subparser for 'task' command
  task_parser = subparsers.add_parser('task', help='Ask a question to ChatGPT and handle the response.')
  task_parser.add_argument('question', help="Question to ask ChatGPT")

  args = parser.parse_args()

  if args.command == 'task':
    messages = [{"role": "user", "content": args.question}]
    initial_response = ask_chatgpt(messages)
    print(f"Placehodlr-FT: {initial_response}")

    filename = extract_filename_from_response(initial_response)
    if not filename:
      print("Error: No valid filename found in the response.")
      sys.exit(1)

    result = fuzzy_search_filepath(filename)
    if not result:
      print(f"Error: No file matching '{filename}' found in MongoDB.")
      sys.exit(1)
    print(result)

    file_url = result["adapterInfo"]["chatGptAdapter"]["fileUrl"]
    if not file_url:
      print("Error: No file URL found in MongoDB entry.")
      sys.exit(1)

    download_file(file_url, filename)

    extra_vars = result["adapterInfo"]["chatGptAdapter"].get("extraVars", {})
    if extra_vars:
      user_vars = prompt_for_extra_vars(extra_vars)
      formatted_extra_vars = format_extra_vars(user_vars)
    else:
      formatted_extra_vars = ""

    run_ansible_playbook(filename, formatted_extra_vars)

if __name__ == "__main__":
  main()
