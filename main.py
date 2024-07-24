import logging
import sys
from pathlib import Path
import json
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from snapshot.capture import save_project_contents
from snapshot.exceptions import ProjectSnapshotError
from snapshot.utils import copy_to_clipboard

CONFIG_FILE = 'config.json'
console = Console()

def configure_logging():
    """Configure logging settings for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("project_snapshot.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

def load_config():
    """
    Load configuration from the JSON file.

    Returns:
        dict: The configuration dictionary.
    """
    if Path(CONFIG_FILE).exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.error(f"Error decoding {CONFIG_FILE}. Using default configuration.")
    return {}

def save_config(new_config):
    """
    Save configuration to the JSON file.

    Args:
        new_config (dict): The new configuration to save.
    """
    existing_config = load_config()
    existing_config.update(new_config)
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(existing_config, f, indent=4)
    except IOError:
        logging.error(f"Error writing to {CONFIG_FILE}.")

def get_target_directory(config):
    """
    Prompt user for the target directory.

    Args:
        config (dict): The current configuration.

    Returns:
        Path: The selected target directory.
    """
    current_directory = config.get('target_directory', str(Path.cwd()))
    console.print(Panel(f"Current target directory: [cyan]{current_directory}[/cyan]"))
    if Confirm.ask("Would you like to update the target directory?"):
        while True:
            new_directory = Prompt.ask("Enter new target directory")
            if Path(new_directory).is_dir():
                return Path(new_directory)
            else:
                console.print("[red]Invalid directory. Please try again.[/red]")
    return Path(current_directory)

def get_project_name(directory):
    """
    Prompt user for the project name.

    Args:
        directory (Path): The target directory.

    Returns:
        str: The selected project name.
    """
    default_name = directory.name
    if Confirm.ask(f"Use '[cyan]{default_name}[/cyan]' as the project name?"):
        return default_name
    return Prompt.ask("Enter custom project name")

def get_output_filename(project_name):
    """
    Generate or prompt for the output filename.

    Args:
        project_name (str): The project name.

    Returns:
        str: The selected output filename.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    default_filename = f"{project_name}_contents-{timestamp}.md"
    if Confirm.ask(f"Use '[cyan]{default_filename}[/cyan]' as the output filename?"):
        return default_filename
    return Prompt.ask("Enter custom filename (timestamp will be appended)")

def main():
    """
    Main function to execute the project snapshot tool.

    This function orchestrates the entire process of capturing
    and saving the project contents.
    """
    try:
        configure_logging()
        config = load_config()
        
        if not config:
            console.print("[yellow]No existing configuration found. We'll create one as we go.[/yellow]")
        
        console.print(Panel.fit("Welcome to [bold green]Project Snapshot[/bold green] - AI-Ready Project Capture Tool", 
                                border_style="bold blue"))

        root_directory = get_target_directory(config)
        save_config({'target_directory': str(root_directory)})
        
        project_name = get_project_name(root_directory)
        
        output_dir = Path('output') / project_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_filename = get_output_filename(project_name)
        output_path = output_dir / output_filename

        include_in_prompt = Confirm.ask("Include project content in AI prompt?")

        with console.status("[bold green]Capturing project contents...[/bold green]"):
            save_project_contents(root_directory, output_path, project_name, include_in_prompt)

        console.print("[bold green]Done! Project snapshot saved and ready for AI analysis.[/bold green]")

        console.print(f"\nOutput saved to: [cyan]{output_path}[/cyan]")
        
        if Confirm.ask("Would you like to copy the output path to clipboard?"):
            copy_to_clipboard(str(output_path))
            console.print("[green]Output path copied to clipboard.[/green]")

        console.print("[bold green]Thank you for using Project Snapshot. Goodbye![/bold green]")

    except ProjectSnapshotError as e:
        console.print(f"[bold red]Project snapshot error: {str(e)}[/bold red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error occurred: {str(e)}[/bold red]")
        logging.exception("An unexpected error occurred")
        sys.exit(1)

if __name__ == "__main__":
    main()