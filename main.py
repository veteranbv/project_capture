import json
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console  # type: ignore
from rich.panel import Panel  # type: ignore
from rich.progress import Progress, SpinnerColumn, TextColumn  # type: ignore
from rich.prompt import Confirm, Prompt  # type: ignore
from rich.table import Table  # type: ignore

from snapshot.capture import save_project_contents
from snapshot.exceptions import ProjectSnapshotError
from snapshot.utils import configure_logging, copy_to_clipboard, sanitize_filename

CONFIG_FILE = "config.json"
MAX_CONFIGS_PER_PROJECT = 5
console = Console()
logger = configure_logging()


def load_config() -> dict:
    """
    Load configuration from the JSON file with basic validation.

    Returns:
        dict: The loaded configuration or a default configuration if the file doesn't exist or is invalid.
    """
    if Path(CONFIG_FILE).exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                if (
                    not isinstance(config, dict)
                    or "configurations" not in config
                    or not isinstance(config["configurations"], list)
                ):
                    raise ValueError("Invalid configuration structure")
                return config
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(
                f"Error loading {CONFIG_FILE}: {str(e)}. Using default configuration."
            )
    return {"configurations": []}


def save_config(config: dict) -> None:
    """
    Save configuration to the JSON file.

    Args:
        config (dict): The configuration to save.
    """
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
    except IOError as e:
        logger.error(f"Error writing to {CONFIG_FILE}: {str(e)}")


def get_target_directory(config: dict) -> Path:
    """
    Prompt user for the target directory, defaulting to Yes for updates.

    Args:
        config (dict): The current configuration.

    Returns:
        Path: The selected target directory.
    """
    current_directory = config.get("last_directory", str(Path.cwd()))
    console.print(Panel(f"Current target directory: [cyan]{current_directory}[/cyan]"))
    if Confirm.ask("Would you like to update the target directory?", default=True):
        while True:
            new_directory = Prompt.ask("Enter new target directory")
            if Path(new_directory).is_dir():
                return Path(new_directory)
            else:
                console.print("[red]Invalid directory. Please try again.[/red]")
    return Path(current_directory)


def display_configurations(configurations: list) -> None:
    """
    Display available configurations in a table.

    Args:
        configurations (list): List of available configurations.
    """
    table = Table(title="Available configurations")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Project Name", style="magenta")
    table.add_column("Last Used", style="green")
    table.add_column("Output Pattern", style="yellow")
    table.add_column("Include in AI", style="blue")

    for idx, config in enumerate(configurations, start=1):
        table.add_row(
            str(idx),
            config["project_name"],
            config["last_used"],
            config["output_pattern"],
            "Yes" if config["include_in_prompt"] else "No",
        )

    console.print(table)


def get_user_choice(config_count: int) -> str:
    """
    Prompt user for action choice, defaulting to choice "1".

    Args:
        config_count (int): The number of existing configurations.

    Returns:
        str: The user's choice.
    """
    if config_count == 0:
        console.print("\n[yellow]No existing configurations found.[/yellow]")
        return "1"  # Automatically create a new configuration
    elif config_count == 1:
        actions = [
            "[bold green][1][/bold green]. Use the existing configuration (default)",
            "2. Edit the existing configuration",
            "3. Delete the existing configuration",
            "4. Create new configuration",
        ]
        choices = ["1", "2", "3", "4"]
    else:
        actions = [
            f"[bold green][1-{config_count}][/bold green]. Choose an existing configuration (default)",
            f"{config_count + 1}. Edit a configuration",
            f"{config_count + 2}. Delete a configuration",
            f"{config_count + 3}. Create new configuration",
        ]
        choices = [str(i) for i in range(1, config_count + 4)]

    console.print("\nActions:")
    for action in actions:
        console.print(action)

    choice_range = f"[1-{len(choices)}]"
    return Prompt.ask(
        f"\nEnter your choice {choice_range} (press Enter to use existing configuration)",
        choices=choices,
        default="1",
        show_default=True,
    )


def create_or_edit_configuration(
    root_directory: Path, existing_config: dict | None = None
) -> dict:
    """
    Create a new configuration or edit an existing one.

    Args:
        root_directory (Path): The root directory of the project.
        existing_config (dict | None, optional): An existing configuration to edit. Defaults to None.

    Returns:
        dict: The new or updated configuration.
    """
    project_name = (
        existing_config["project_name"] if existing_config else root_directory.name
    )
    timestamp = "{time}"
    default_filename = (
        existing_config["output_pattern"]
        if existing_config
        else f"{project_name}_contents-{timestamp}.md"
    )

    if Confirm.ask(f"Use '[cyan]{project_name}[/cyan]' as the project name?"):
        project_name = project_name
    else:
        project_name = Prompt.ask("Enter project name", default=project_name)
    project_name = sanitize_filename(project_name)

    while True:
        if Confirm.ask(
            f"Use '[cyan]{default_filename}[/cyan]' as the output filename pattern?"
        ):
            output_pattern = default_filename
        else:
            output_pattern = Prompt.ask(
                "Enter the base filename ('{time}' will be appended automatically)",
                default=default_filename.replace("-{time}.md", ""),
            )
            output_pattern = sanitize_filename(output_pattern)
            output_pattern += "-{time}.md"

        try:
            # Test if the pattern is valid
            output_pattern.format(time="test")
            break
        except KeyError:
            console.print(
                "[red]Invalid filename pattern. Please use only '{time}' as a placeholder.[/red]"
            )

    include_in_prompt = Confirm.ask(
        "Include project content in AI prompt?",
        default=existing_config["include_in_prompt"] if existing_config else True,
    )

    # Ask about using gitignore files
    use_local_gitignore = Confirm.ask(
        "Use local .gitignore patterns (from current directory)?",
        default=existing_config.get("use_local_gitignore", True)
        if existing_config
        else True,
    )

    use_project_gitignore = Confirm.ask(
        "Use project .gitignore patterns (from target directory)?",
        default=existing_config.get("use_project_gitignore", True)
        if existing_config
        else True,
    )

    # Get existing ignore patterns or use empty list
    ignore_patterns = (
        existing_config.get("ignore_patterns", []) if existing_config else []
    )

    # Ask if user wants to edit ignore patterns
    if Confirm.ask("Would you like to configure ignore patterns?", default=False):
        console.print("\nYou can either:")
        console.print("1. Point to an existing ignore file")
        console.print("2. Edit patterns directly")
        console.print("3. Skip configuring ignore patterns\n")

        ignore_choice = Prompt.ask(
            "Choose an option", choices=["1", "2", "3"], default="2"
        )

        if ignore_choice == "1":
            console.print(
                "\nEnter the path to your ignore file (relative to project root):"
            )
            console.print("Examples: .gitignore, .npmignore, custom_ignore.txt")
            ignore_file = Prompt.ask("File path")
            ignore_file_path = root_directory / ignore_file

            if ignore_file_path.exists() and ignore_file_path.is_file():
                try:
                    with ignore_file_path.open("r") as f:
                        ignore_patterns = [
                            line.strip()
                            for line in f
                            if line.strip() and not line.startswith("#")
                        ]
                    console.print(
                        f"\n[green]Successfully loaded {len(ignore_patterns)} patterns from {ignore_file}[/green]"
                    )
                except Exception as e:
                    console.print(f"[red]Error reading file: {str(e)}[/red]")
                    console.print("Continuing with existing patterns...")
            else:
                console.print(f"[red]File not found: {ignore_file}[/red]")
                console.print("Continuing with existing patterns...")

        elif ignore_choice == "2":
            console.print(
                "\nIgnore patterns use the same syntax as .gitignore files. For example:"
            )
            console.print("  • *.log         - Ignore all log files")
            console.print("  • build/        - Ignore the build directory")
            console.print("  • test_*.py     - Ignore test files")
            console.print("  • docs/*.md     - Ignore markdown files in docs directory")
            console.print("  • !README.md    - Don't ignore README.md (exception)")
            console.print(
                "\nThese patterns are in addition to your .gitignore files.\n"
            )

            while True:
                console.print("\nCurrent ignore patterns:")
                if ignore_patterns:
                    for i, pattern in enumerate(ignore_patterns, 1):
                        console.print(f"{i}. {pattern}")
                else:
                    console.print("[yellow]No custom ignore patterns defined.[/yellow]")

                console.print("""
1. Add pattern
2. Remove pattern
3. Clear all patterns
4. Done editing
                """)

                action = Prompt.ask(
                    "Choose action",
                    choices=["1", "2", "3", "4"],
                    default="4",
                    show_choices=False,
                )

                if action == "1":
                    new_pattern = Prompt.ask("Enter new ignore pattern")
                    if new_pattern and new_pattern not in ignore_patterns:
                        ignore_patterns.append(new_pattern)
                elif action == "2" and ignore_patterns:
                    pattern_num = Prompt.ask(
                        "Enter pattern number to remove",
                        choices=[str(i) for i in range(1, len(ignore_patterns) + 1)],
                    )
                    ignore_patterns.pop(int(pattern_num) - 1)
                elif action == "3":
                    if Confirm.ask(
                        "Are you sure you want to clear all patterns?", default=False
                    ):
                        ignore_patterns = []
                elif action == "4":
                    break

    return {
        "project_name": project_name,
        "directory": str(root_directory),
        "output_pattern": output_pattern,
        "include_in_prompt": include_in_prompt,
        "use_local_gitignore": use_local_gitignore,
        "use_project_gitignore": use_project_gitignore,
        "ignore_patterns": ignore_patterns,
        "last_used": datetime.now().strftime("%Y-%m-%d"),
    }


def is_duplicate_config(new_config: dict, existing_configs: list) -> bool:
    """
    Check if a configuration is a duplicate of an existing one.

    Args:
        new_config (dict): The new configuration to check.
        existing_configs (list): List of existing configurations.

    Returns:
        bool: True if the configuration is a duplicate, False otherwise.
    """
    for config in existing_configs:
        if (
            config["project_name"] == new_config["project_name"]
            and config["directory"] == new_config["directory"]
            and config["output_pattern"] == new_config["output_pattern"]
            and config["include_in_prompt"] == new_config["include_in_prompt"]
        ):
            return True
    return False


def delete_configuration(config: dict, index: int) -> None:
    """
    Delete a configuration from the list.

    Args:
        config (dict): The configuration dictionary.
        index (int): The index of the configuration to delete.
    """
    del config["configurations"][index]


def edit_configuration(config: dict, index: int, new_config: dict) -> None:
    """
    Edit an existing configuration.

    Args:
        config (dict): The configuration dictionary.
        index (int): The index of the configuration to edit.
        new_config (dict): The new configuration data.
    """
    config["configurations"][index] = new_config


def add_configuration(config: dict, new_config: dict) -> None:
    """
    Add a new configuration using FIFO if the limit is reached.

    Args:
        config (dict): The main configuration dictionary.
        new_config (dict): The new configuration to add.
    """
    matching_configs = [
        c for c in config["configurations"] if c["directory"] == new_config["directory"]
    ]

    if len(matching_configs) >= MAX_CONFIGS_PER_PROJECT:
        # Remove the oldest configuration for this project
        oldest_config = min(
            matching_configs,
            key=lambda x: datetime.strptime(x["last_used"], "%Y-%m-%d"),
        )
        config["configurations"].remove(oldest_config)
        logger.info(f"Removed oldest configuration for {new_config['project_name']}")

    config["configurations"].append(new_config)
    logger.info(f"Added new configuration for {new_config['project_name']}")


def main():
    """Main function to execute the project snapshot tool."""
    try:
        config = load_config()

        console.print(
            Panel.fit(
                "Welcome to [bold green]Project Snapshot[/bold green] - AI-Ready Project Capture Tool",
                border_style="bold blue",
            )
        )

        root_directory = get_target_directory(config)
        config["last_directory"] = str(root_directory)

        matching_configs = [
            c for c in config["configurations"] if c["directory"] == str(root_directory)
        ]

        while True:
            if matching_configs:
                display_configurations(matching_configs)
                choice = get_user_choice(len(matching_configs))

                if choice.isdigit() and 1 <= int(choice) <= len(matching_configs):
                    selected_config = matching_configs[int(choice) - 1]
                    break
                elif choice == str(len(matching_configs) + 1):  # Edit
                    edit_choice = Prompt.ask(
                        "Enter the ID of the configuration to edit",
                        choices=[str(i) for i in range(1, len(matching_configs) + 1)],
                    )
                    index = int(edit_choice) - 1
                    edited_config = create_or_edit_configuration(
                        root_directory, matching_configs[index]
                    )
                    edit_configuration(
                        config,
                        config["configurations"].index(matching_configs[index]),
                        edited_config,
                    )
                    matching_configs[index] = edited_config
                    selected_config = edited_config
                    save_config(config)
                    break
                elif choice == str(len(matching_configs) + 2):  # Delete
                    delete_choice = Prompt.ask(
                        "Enter the ID of the configuration to delete",
                        choices=[str(i) for i in range(1, len(matching_configs) + 1)],
                    )
                    index = int(delete_choice) - 1
                    config_index = config["configurations"].index(
                        matching_configs[index]
                    )
                    deleted_config = config["configurations"].pop(config_index)
                    matching_configs.pop(index)
                    save_config(config)
                    console.print(
                        f"[green]Configuration '{deleted_config['project_name']}' deleted successfully.[/green]"
                    )
                    if not matching_configs:
                        console.print(
                            "[yellow]No configurations left. Creating a new one.[/yellow]"
                        )
                        new_config = create_or_edit_configuration(root_directory)
                        add_configuration(config, new_config)
                        matching_configs.append(new_config)
                        selected_config = new_config
                        save_config(config)
                        break
                    continue
                elif choice == str(len(matching_configs) + 3):  # Create new
                    new_config = create_or_edit_configuration(root_directory)
                    if is_duplicate_config(new_config, matching_configs):
                        console.print(
                            "[yellow]A duplicate configuration already exists. Using the existing configuration.[/yellow]"
                        )
                        selected_config = next(
                            c
                            for c in matching_configs
                            if c["project_name"] == new_config["project_name"]
                        )
                    else:
                        add_configuration(config, new_config)
                        matching_configs.append(new_config)
                        selected_config = new_config
                    save_config(config)
                    break
            else:
                console.print(
                    Panel(
                        "[yellow]No existing configurations found for this directory.[/yellow]",
                        expand=False,
                    )
                )
                console.print()
                selected_config = create_or_edit_configuration(root_directory)
                add_configuration(config, selected_config)
                save_config(config)
                break

        selected_config["last_used"] = datetime.now().strftime("%Y-%m-%d")
        save_config(config)

        console.print(
            f"\nUsing configuration: [cyan]{selected_config['project_name']}[/cyan]"
        )
        console.print(
            f"Output pattern: [cyan]{selected_config['output_pattern']}[/cyan]"
        )
        console.print(
            f"Include in AI prompt: {'[green]Yes[/green]' if selected_config['include_in_prompt'] else '[red]No[/red]'}"
        )

        output_filename = selected_config["output_pattern"].format(
            time=datetime.now().strftime("%Y-%m-%d-%H%M%S")
        )
        output_path = (
            Path(__file__).resolve().parent
            / "output"
            / selected_config["project_name"]
            / output_filename
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Capturing project contents...", total=None)
            result = save_project_contents(
                root_directory,
                output_path,
                selected_config["project_name"],
                selected_config["include_in_prompt"],
                selected_config.get("ignore_patterns", []),
                selected_config.get("use_local_gitignore", True),
                selected_config.get("use_project_gitignore", True),
            )

        console.print(
            Panel("Project snapshot saved successfully!", expand=False, style="green")
        )
        console.print(f"\nOutput saved to: [cyan]{output_path}[/cyan]")

        console.print(
            Panel(
                f"Processed: {result['processed']} files\n"
                f"Skipped: {result['skipped']} non-text files\n"
                f"Errors: {len(result['errors'])}",
                title="Summary",
                expand=False,
            )
        )

        if result["errors"]:
            console.print(
                "\n[bold yellow]Note:[/bold yellow] Some errors were encountered. Check the log file for details."
            )

        if Confirm.ask(
            "Would you like to copy the output path to clipboard?", default=False
        ):
            if copy_to_clipboard(str(output_path)):
                console.print("[green]Output path copied to clipboard.[/green]")
            else:
                console.print(
                    "[yellow]Failed to copy to clipboard. Please copy the path manually.[/yellow]"
                )

        console.print(
            "[bold green]Thank you for using Project Snapshot. Goodbye![/bold green]"
        )

    except ProjectSnapshotError as e:
        logger.error(f"Project snapshot error: {str(e)}")
        console.print(f"[bold red]Project snapshot error: {str(e)}[/bold red]")
        sys.exit(1)
    except Exception as e:
        logger.exception("An unexpected error occurred")
        console.print(f"[bold red]Unexpected error occurred: {str(e)}[/bold red]")
        console.print("[yellow]Please check the log file for details.[/yellow]")
        sys.exit(1)


if __name__ == "__main__":
    main()
