#!/bin/bash

# Exit on errors to prevent unexpected behavior
set -e

# Function to download and install a package using sudo apt
install_package() {
  local package_name="$1"
  if [[ ! $(dpkg-query -l "$package_name" 2>/dev/null | grep installed) ]]; then
    echo "Installing $package_name..."
    sudo apt install -y "$package_name"
  else
    echo "$package_name already installed."
  fi
}

# Function to download and install Python 3 and pip
install_python3_and_pip() {
  printf "Installing Python3 and PIP\n"
  install_package software-properties-common
  sudo add-apt-repository ppa:deadsnakes/ppa -y  # Latest Python 3 versions
  sudo apt update -y
  install_package python3
  install_package python3-pip
}

# Function to download and install Ansible
install_ansible() {
  printf "Installing Ansible\n"
  install_package ansible
}

# Function to create ansible.cfg with log_path and callback settings
create_ansible_cfg() {
  printf "Creating Ansible Config\n"
  local current_path="$(pwd)"
  local ansible_cfg_path="$current_path/ansible.cfg"

  cat <<EOF > "$ansible_cfg_path"
[defaults]
log_path = $current_path/ansible.log
callback_plugins = $current_path/plugins
callback_whitelist = log_to_mongod
EOF

  echo "Created ansible.cfg at $ansible_cfg_path"
}

# Function to download and install MongoDB
install_mongodb() {
  # Official MongoDB repository setup instructions for Ubuntu/Debian:
  # https://www.mongodb.com/docs/manual/current/install-on-debian.html
  printf "Installing MongoDB\n"
  wget -qO - https://www.mongodb.org/static/public-pgp-key-file
  echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/stable multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-stable.list
  sudo apt update -y
  install_package mongodb-org-server

  # Enable and start MongoDB service
  sudo systemctl enable mongod
  sudo systemctl start mongod
}

# Function to download and install dependencies for the import code
install_import_code_dependencies() {
  printf "Installing Core Dependencies\n"
  install_package python3-dev
  install_package libssl-dev
  pip install openai
  pip install pymongo
  # Other dependencies can be added here based on the import code's requirements
}

# Function to create the log_to_mongod callback plugin
create_log_to_mongod_callback() {
  printf "Setting up Plugins and Mongo Path\n"
  local plugins_path="$(pwd)/plugins"  # Ensure path is relative to current working directory
  local callback_script_path="$plugins_path/log_to_mongod.py"
  local callback_script_url="https://raw.githubusercontent.com/ankit2771991/ymls/main/script/log_to_mongodb.py"  # Replace with the actual URL

  # Create the plugins directory only if it doesn't exist
  if [[ ! -d "$plugins_path" ]]; then
    mkdir -p "$plugins_path"
  fi

  # Download the callback script from the provided URL
  if curl -o "$callback_script_path" "$callback_script_url"; then
    echo "Downloaded log_to_mongod.py to $callback_script_path"
  else
    echo "Failed to download log_to_mongod.py"
    exit 1
  fi
}

# Function to download placehodlr_ft.py from URL
download_placehodlr_ft() {
  local python_file_url="https://raw.githubusercontent.com/ankit2771991/ymls/main/script/placehodlr-cli.py"  # Replace with the actual URL
  local python_file_path="placehodlr_ft.py"

  echo "Downloading placehodlr_ft.py from $python_file_url..."

  if curl -o "$python_file_path" "$python_file_url"; then
    echo "Downloaded placehodlr_ft.py to $python_file_path"
    chmod +x "$python_file_path"
  else
    echo "Failed to download placehodlr_ft.py"
    exit 1
  fi
}

# Function to prompt the user for environment variable values if not set
prompt_for_env_vars() {
  local var_name="$1"
  local prompt_message="$2"
  local env_value="${!var_name}"

  if [[ -z "$env_value" ]]; then
    read -p "$prompt_message: " env_value
    export "$var_name"="$env_value"
    echo "Set $var_name"
  else
    echo "$var_name is already set to: $env_value"
  fi
}

# Main execution
install_python3_and_pip
install_ansible
create_ansible_cfg
# install_mongodb  # Uncomment if MongoDB is required
install_import_code_dependencies
create_log_to_mongod_callback
download_placehodlr_ft

# Prompt for and display environment variables
prompt_for_env_vars "OPENAI_API_KEY" "Enter your OpenAI API Key"
prompt_for_env_vars "MONGODB_URI" "Enter your MongoDB URI"
prompt_for_env_vars "OPENAI_MODEL_KEY" "Enter your OpenAI Model Key"

# Run the downloaded Python script
echo "Running placehodlr_ft.py..."
./placehodlr_ft.py
