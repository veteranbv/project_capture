import os
import logging
from dotenv import load_dotenv
from snapshot.capture import save_project_contents

def load_environment():
    """Load environment variables from .env file."""
    load_dotenv()

def configure_logging():
    """Configure logging settings."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_root_directory():
    """Retrieve the root directory from environment variables."""
    root_directory = os.getenv('DIRECTORY')
    if root_directory is None:
        logging.error("DIRECTORY environment variable not set.")
        exit(1)

    # Handle both single and double quotes
    if root_directory.startswith('"') and root_directory.endswith('"'):
        root_directory = root_directory[1:-1]
    elif root_directory.startswith("'") and root_directory.endswith("'"):
        root_directory = root_directory[1:-1]

    return root_directory

def check_directory_exists(directory):
    """Check if the specified directory exists."""
    if not os.path.exists(directory):
        logging.error(f"Target directory does not exist: {directory}")
        exit(1)

def main():
    configure_logging()

    # Check if .env file exists
    env_file_path = os.path.join(os.getcwd(), '.env')
    if not os.path.exists(env_file_path):
        logging.error(".env file not found.")
        exit(1)

    logging.info(f".env file found at: {env_file_path}")
    load_environment()

    root_directory = get_root_directory()
    logging.info(f"Target directory found: {root_directory}")

    check_directory_exists(root_directory)

    output_dir = 'output'
    output_filename = os.path.join(output_dir, 'project_contents.md')
    os.makedirs(output_dir, exist_ok=True)

    save_project_contents(root_directory, output_filename)
    logging.info("Project contents saved to: %s", output_filename)

if __name__ == "__main__":
    main()