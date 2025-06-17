import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from rich.console import Console  # type: ignore
from rich.panel import Panel  # type: ignore
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn  # type: ignore
from rich.prompt import Confirm, Prompt  # type: ignore
from rich.table import Table  # type: ignore

from project_capture.core.capture import save_project_contents
from project_capture.core.config import (
    CONFIG_FILE,
    MAX_CONFIGS_PER_PROJECT,
    add_configuration,
    create_default_config,
    delete_configuration,
    is_duplicate_config,
    load_config,
    save_config,
    update_configuration,
)
from project_capture.core.constants import IGNORE_PATTERN_TEMPLATES
from project_capture.core.exceptions import ProjectSnapshotError
from project_capture.core.types import AppConfig, ProjectConfig, ProjectContentsResult
from project_capture.core.utils import (
    configure_logging,
    copy_to_clipboard,
    get_output_path,
    sanitize_filename,
)

# Initialize console and logger
console = Console()
logger = configure_logging()




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


def display_template_patterns(template_name: str) -> None:
    """
    Display the patterns in the specified template.
    
    Args:
        template_name (str): Name of the template to display
    """
    if template_name not in IGNORE_PATTERN_TEMPLATES:
        console.print(f"[red]Template '{template_name}' not found[/red]")
        return
        
    patterns = IGNORE_PATTERN_TEMPLATES[template_name]
    console.print(f"\n[bold cyan]{template_name}[/bold cyan] ignore patterns:")
    
    for i, pattern in enumerate(patterns, 1):
        console.print(f"{i}. {pattern}")
    console.print()


def create_or_edit_configuration(
    root_directory: Path, existing_config: Optional[ProjectConfig] = None
) -> ProjectConfig:
    """
    Create a new configuration or edit an existing one with an improved interface.

    Args:
        root_directory (Path): The root directory of the project.
        existing_config (Optional[ProjectConfig]): An existing configuration to edit. Defaults to None.

    Returns:
        ProjectConfig: The new or updated configuration.
    """
    # Default values
    project_name = existing_config["project_name"] if existing_config else root_directory.name
    timestamp = "{time}"
    default_filename = (
        existing_config["output_pattern"]
        if existing_config
        else f"{project_name}_contents-{timestamp}.md"
    )

    # Project name
    console.print(Panel("Configure Project", style="cyan"))
    if Confirm.ask(f"Use '[cyan]{project_name}[/cyan]' as the project name?"):
        project_name = project_name
    else:
        project_name = Prompt.ask("Enter project name", default=project_name)
    project_name = sanitize_filename(project_name)

    # Output filename pattern
    while True:
        if Confirm.ask(f"Use '[cyan]{default_filename}[/cyan]' as the output filename pattern?"):
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

    # AI prompt inclusion
    include_in_prompt = Confirm.ask(
        "Include project content in AI prompt?",
        default=existing_config["include_in_prompt"] if existing_config else True,
    )

    # Performance settings
    console.print(Panel("Performance Settings", style="green"))
    use_parallel_processing = Confirm.ask(
        "Use parallel processing for faster file processing?",
        default=existing_config.get("use_parallel_processing", True) if existing_config else True,
    )
    
    check_binary_content = Confirm.ask(
        "Check file content to detect binary files? (more accurate but slower)",
        default=existing_config.get("check_binary_content", True) if existing_config else True,
    )

    # Gitignore settings
    console.print(Panel("Gitignore Settings", style="yellow"))
    use_local_gitignore = Confirm.ask(
        "Use local .gitignore patterns (from current directory)?",
        default=existing_config.get("use_local_gitignore", True) if existing_config else True,
    )

    use_project_gitignore = Confirm.ask(
        "Use project .gitignore patterns (from target directory)?",
        default=existing_config.get("use_project_gitignore", True) if existing_config else True,
    )

    # Get existing ignore patterns or use empty list
    ignore_patterns = existing_config.get("ignore_patterns", []) if existing_config else []

    # Pattern configuration
    if Confirm.ask("Would you like to configure ignore patterns?", default=False):
        console.print(Panel("Ignore Pattern Configuration", style="magenta"))
        console.print("\nYou can:")
        console.print("1. Point to an existing ignore file")
        console.print("2. Use a predefined template")
        console.print("3. Edit patterns directly")
        console.print("4. Skip configuring ignore patterns\n")

        ignore_choice = Prompt.ask(
            "Choose an option", choices=["1", "2", "3", "4"], default="3"
        )

        # Option 1: Use existing file
        if ignore_choice == "1":
            console.print("\nEnter the path to your ignore file (relative to project root):")
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
                
        # Option 2: Use predefined template
        elif ignore_choice == "2":
            console.print("\nAvailable templates:")
            for i, template_name in enumerate(IGNORE_PATTERN_TEMPLATES.keys(), 1):
                console.print(f"{i}. {template_name}")
                
            template_choices = list(map(str, range(1, len(IGNORE_PATTERN_TEMPLATES) + 1)))
            template_idx = int(Prompt.ask(
                "Choose a template", 
                choices=template_choices,
                default="1"
            ))
            
            template_name = list(IGNORE_PATTERN_TEMPLATES.keys())[template_idx - 1]
            display_template_patterns(template_name)
            
            if Confirm.ask(f"Add [cyan]{template_name}[/cyan] patterns to your configuration?", default=True):
                # Add template patterns to current patterns, avoiding duplicates
                new_patterns = IGNORE_PATTERN_TEMPLATES[template_name]
                for pattern in new_patterns:
                    if pattern not in ignore_patterns:
                        ignore_patterns.append(pattern)
                console.print(f"[green]Added {template_name} patterns to your configuration[/green]")

        # Option 3: Edit patterns directly
        elif ignore_choice == "3":
            console.print(
                "\nIgnore patterns use the same syntax as .gitignore files. For example:"
            )
            console.print("  • *.log         - Ignore all log files")
            console.print("  • build/        - Ignore the build directory")
            console.print("  • test_*.py     - Ignore test files")
            console.print("  • docs/*.md     - Ignore markdown files in docs directory")
            console.print("  • !README.md    - Don't ignore README.md (exception)")
            console.print("\nThese patterns are in addition to your .gitignore files.\n")

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
4. Use template
5. Done editing
                """)

                action = Prompt.ask(
                    "Choose action",
                    choices=["1", "2", "3", "4", "5"],
                    default="5",
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
                    if Confirm.ask("Are you sure you want to clear all patterns?", default=False):
                        ignore_patterns = []
                elif action == "4":
                    console.print("\nAvailable templates:")
                    for i, template_name in enumerate(IGNORE_PATTERN_TEMPLATES.keys(), 1):
                        console.print(f"{i}. {template_name}")
                        
                    template_choices = list(map(str, range(1, len(IGNORE_PATTERN_TEMPLATES) + 1)))
                    template_idx = int(Prompt.ask(
                        "Choose a template", 
                        choices=template_choices,
                        default="1"
                    ))
                    
                    template_name = list(IGNORE_PATTERN_TEMPLATES.keys())[template_idx - 1]
                    display_template_patterns(template_name)
                    
                    if Confirm.ask(f"Add [cyan]{template_name}[/cyan] patterns to your configuration?", default=True):
                        # Add template patterns to current patterns, avoiding duplicates
                        new_patterns = IGNORE_PATTERN_TEMPLATES[template_name]
                        for pattern in new_patterns:
                            if pattern not in ignore_patterns:
                                ignore_patterns.append(pattern)
                        console.print(f"[green]Added {template_name} patterns to your configuration[/green]")
                elif action == "5":
                    break

    # Create the configuration with all our new options
    config = {
        # Basic settings
        "project_name": project_name,
        "directory": str(root_directory),
        "output_pattern": output_pattern,
        "include_in_prompt": include_in_prompt,
        
        # Gitignore settings
        "use_local_gitignore": use_local_gitignore,
        "use_project_gitignore": use_project_gitignore,
        "ignore_patterns": ignore_patterns,
        
        # Performance settings
        "use_parallel_processing": use_parallel_processing,
        "check_binary_content": check_binary_content,
        
        # Format settings (default to markdown for now)
        "output_format": "markdown",
        
        # Metadata
        "last_used": datetime.now().strftime("%Y-%m-%d"),
    }
    
    return cast(ProjectConfig, config)


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
        # Load app configuration
        app_config = load_config()

        # Welcome message
        console.print(
            Panel.fit(
                "Welcome to [bold green]Project Snapshot[/bold green] - AI-Ready Project Capture Tool",
                border_style="bold blue",
            )
        )

        # Get target directory
        root_directory = get_target_directory(app_config)
        app_config["last_directory"] = str(root_directory)

        # Find configurations matching the current directory
        matching_configs = [
            c for c in app_config["configurations"] if c["directory"] == str(root_directory)
        ]

        # Configuration selection/creation loop
        while True:
            if matching_configs:
                display_configurations(matching_configs)
                choice = get_user_choice(len(matching_configs))

                # Use existing configuration
                if choice.isdigit() and 1 <= int(choice) <= len(matching_configs):
                    selected_config = matching_configs[int(choice) - 1]
                    break
                    
                # Edit configuration
                elif choice == str(len(matching_configs) + 1):  
                    edit_choice = Prompt.ask(
                        "Enter the ID of the configuration to edit",
                        choices=[str(i) for i in range(1, len(matching_configs) + 1)],
                    )
                    index = int(edit_choice) - 1
                    
                    # Cast to ProjectConfig for type safety
                    config_to_edit = cast(ProjectConfig, matching_configs[index])
                    edited_config = create_or_edit_configuration(root_directory, config_to_edit)
                    
                    # Update in the main config
                    config_index = app_config["configurations"].index(matching_configs[index])
                    update_configuration(app_config, config_index, edited_config)
                    
                    matching_configs[index] = edited_config
                    selected_config = edited_config
                    save_config(app_config)
                    break
                    
                # Delete configuration
                elif choice == str(len(matching_configs) + 2):  
                    delete_choice = Prompt.ask(
                        "Enter the ID of the configuration to delete",
                        choices=[str(i) for i in range(1, len(matching_configs) + 1)],
                    )
                    index = int(delete_choice) - 1
                    config_index = app_config["configurations"].index(matching_configs[index])
                    
                    # Delete from main config
                    deleted_config = app_config["configurations"].pop(config_index)
                    matching_configs.pop(index)
                    save_config(app_config)
                    
                    console.print(
                        f"[green]Configuration '{deleted_config['project_name']}' deleted successfully.[/green]"
                    )
                    
                    # If no configs left, create a new one
                    if not matching_configs:
                        console.print(
                            "[yellow]No configurations left. Creating a new one.[/yellow]"
                        )
                        new_config = create_or_edit_configuration(root_directory)
                        add_configuration(app_config, new_config)
                        matching_configs.append(new_config)
                        selected_config = new_config
                        save_config(app_config)
                        break
                    continue
                    
                # Create new configuration
                elif choice == str(len(matching_configs) + 3):  
                    new_config = create_or_edit_configuration(root_directory)
                    
                    if is_duplicate_config(new_config, matching_configs):
                        console.print(
                            "[yellow]A duplicate configuration already exists. Using the existing configuration.[/yellow]"
                        )
                        selected_config = next(
                            c for c in matching_configs 
                            if c["project_name"] == new_config["project_name"]
                        )
                    else:
                        add_configuration(app_config, new_config)
                        matching_configs.append(new_config)
                        selected_config = new_config
                        
                    save_config(app_config)
                    break
            else:
                # No configs found, create a new one
                console.print(
                    Panel(
                        "[yellow]No existing configurations found for this directory.[/yellow]",
                        expand=False,
                    )
                )
                console.print()
                selected_config = create_or_edit_configuration(root_directory)
                add_configuration(app_config, selected_config)
                save_config(app_config)
                break

        # Update last used timestamp
        selected_config["last_used"] = datetime.now().strftime("%Y-%m-%d")
        save_config(app_config)

        # Display selected configuration
        console.print(
            Panel(
                f"Configuration: [cyan]{selected_config['project_name']}[/cyan]\n"
                f"Output pattern: [cyan]{selected_config['output_pattern']}[/cyan]\n"
                f"Include in AI prompt: {'[green]Yes[/green]' if selected_config['include_in_prompt'] else '[red]No[/red]'}\n"
                f"Parallel processing: {'[green]Yes[/green]' if selected_config.get('use_parallel_processing', True) else '[red]No[/red]'}\n"
                f"Binary content detection: {'[green]Yes[/green]' if selected_config.get('check_binary_content', True) else '[red]No[/red]'}",
                title="Selected Configuration",
                expand=False,
            )
        )

        # Calculate output path
        output_path = get_output_path(
            selected_config["project_name"], 
            selected_config["output_pattern"]
        )
        
        # Display start message
        console.print(Panel("Starting project snapshot...", style="cyan", expand=False))
        start_time = time.time()

        # Run snapshot with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            transient=True,
        ) as progress:
            progress.add_task(description="Capturing project contents...", total=None)
            
            # Extract all relevant settings from configuration
            result = save_project_contents(
                root_directory,
                output_path,
                selected_config["project_name"],
                selected_config["include_in_prompt"],
                selected_config.get("ignore_patterns", []),
                selected_config.get("use_local_gitignore", True),
                selected_config.get("use_project_gitignore", True),
                selected_config.get("use_parallel_processing", True),
                None,  # Use default max_workers
                selected_config.get("check_binary_content", True),
            )

        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        
        # Success message
        console.print(
            Panel("Project snapshot saved successfully!", expand=False, style="green")
        )
        console.print(f"\nOutput saved to: [cyan]{output_path}[/cyan]")

        # Display summary
        console.print(
            Panel(
                f"Processed: {result['processed']} files\n"
                f"Skipped: {result['skipped']} non-text files\n"
                f"Errors: {len(result['errors'])}\n"
                f"Time taken: {elapsed_time:.2f} seconds",
                title="Summary",
                expand=False,
            )
        )

        # Handle errors if any
        if result["errors"]:
            console.print(
                "\n[bold yellow]Note:[/bold yellow] Some errors were encountered. Check the log file for details."
            )
            if Confirm.ask("Would you like to see the errors?", default=False):
                for i, error in enumerate(result["errors"], 1):
                    console.print(f"{i}. [yellow]{error}[/yellow]")

        # Clipboard option
        if Confirm.ask(
            "Would you like to copy the output path to clipboard?", default=False
        ):
            if copy_to_clipboard(str(output_path)):
                console.print("[green]Output path copied to clipboard.[/green]")
            else:
                console.print(
                    "[yellow]Failed to copy to clipboard. Please copy the path manually.[/yellow]"
                )

        # Goodbye message
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
