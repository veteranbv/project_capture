import logging
from dotenv import load_dotenv
from snapshot.capture import save_project_contents
from pathlib import Path

def load_environment():
    """Load environment variables from .env file."""
    env_file = Path.cwd() / '.env'
    if not env_file.exists():
        logging.error(".env file not found.")
        exit(1)
    logging.info(f".env file found at: {env_file}")
    load_dotenv(env_file)

def configure_logging():
    """Configure logging settings."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_root_directory():
    """Retrieve the root directory from environment variables."""
    from os import getenv
    root_directory = getenv('DIRECTORY')
    if not root_directory:
        logging.error("DIRECTORY environment variable not set.")
        exit(1)
    return Path(root_directory.strip("'\""))

def main():
    configure_logging()
    load_environment()

    root_directory = get_root_directory()
    logging.info(f"Target directory found: {root_directory}")

    if not root_directory.exists():
        logging.error(f"Target directory does not exist: {root_directory}")
        exit(1)

    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    output_filename = output_dir / 'project_contents.md'

    save_project_contents(root_directory, output_filename)
    logging.info(f"Project contents saved to: {output_filename}")

if __name__ == "__main__":
    main()