import json
from datetime import datetime
from pathlib import Path
from typing import cast

import streamlit as st  # type: ignore

from snapshot.capture import save_project_contents
from snapshot.types import (
    AppConfig,
    ProjectConfig,
    is_valid_app_config,
    is_valid_project_config,
)
from snapshot.utils import configure_logging, copy_to_clipboard, sanitize_filename

# Configure logging
logger = configure_logging()

CONFIG_FILE = "config.json"
MAX_CONFIGS_PER_PROJECT = 5


def create_default_config(root_directory: str | Path) -> ProjectConfig:
    """Create a default configuration for a directory.

    Args:
        root_directory (str | Path): The root directory path

    Returns:
        ProjectConfig: A default configuration
    """
    name = Path(root_directory).name
    config = {  # type: ignore
        "project_name": name,
        "directory": str(root_directory),
        "output_pattern": f"{name}_contents-{{time}}.md",
        "include_in_prompt": True,
        "ignore_patterns": [],
        "last_used": datetime.now().strftime("%Y-%m-%d"),
    }
    assert is_valid_project_config(config)
    return cast(ProjectConfig, config)


# Load config
@st.cache_data
def load_config() -> AppConfig:
    """Load configuration from the JSON file with basic validation.

    Returns:
        AppConfig: The configuration dictionary containing a list of project configurations
    """
    if Path(CONFIG_FILE).exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                if not is_valid_app_config(config):
                    raise ValueError("Invalid configuration structure")
                return cast(AppConfig, config)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(
                f"Error loading {CONFIG_FILE}: {str(e)}. Using default configuration."
            )
    return cast(AppConfig, {"configurations": []})


# Save config
def save_config(config: AppConfig) -> None:
    """Save configuration to the JSON file.

    Args:
        config (AppConfig): The configuration dictionary to save
    """
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
    except IOError as e:
        logger.error(f"Error writing to {CONFIG_FILE}: {str(e)}")


def get_subdirectories(path: str | Path) -> list[Path]:
    """Get all subdirectories in the given path.

    Args:
        path (str | Path): The directory path to scan

    Returns:
        list[Path]: List of subdirectory paths
    """
    return [d for d in Path(path).iterdir() if d.is_dir()]


def main():
    st.set_page_config(page_title="Project Snapshot", layout="wide")
    st.title("Project Snapshot")

    # Load configuration
    config = load_config()

    # Directory selection
    root_directory = st.text_input("Project Directory", value=str(Path.cwd()))
    if not Path(root_directory).is_dir():
        st.error("Invalid directory path")
        return

    # Get configurations for current directory
    matching_configs = [
        cast(ProjectConfig, c)
        for c in config["configurations"]  # type: ignore
        if c["directory"] == root_directory
    ]

    # Configuration management
    st.subheader("Configuration Management")

    col1, col2 = st.columns([2, 1])

    with col1:
        if matching_configs:
            config_names = [c["project_name"] for c in matching_configs]
            config_names.append("Create New")
            selected_name = st.selectbox(
                "Select Configuration",
                options=config_names,
                index=0
                if "selected_config" not in st.session_state
                else config_names.index(
                    st.session_state.selected_config["project_name"]  # type: ignore
                ),
            )

            if selected_name == "Create New":
                action = "Create"
                selected_config = create_default_config(root_directory)
            else:
                selected_config = next(
                    c for c in matching_configs if c["project_name"] == selected_name
                )
                action = st.radio("Action", ["Use", "Edit", "Delete"], horizontal=True)
        else:
            st.info("No configurations found for this directory")
            action = "Create"
            selected_config = create_default_config(root_directory)

    # Configuration form
    if action in ["Create", "Edit"]:
        with st.form("config_form"):
            st.subheader(f"{'Create' if action == 'Create' else 'Edit'} Configuration")

            project_name = st.text_input(
                "Project Name",
                value=selected_config["project_name"],  # type: ignore
            )
            output_pattern = st.text_input(
                "Output Pattern",
                value=selected_config["output_pattern"],  # type: ignore
            )
            include_in_prompt = st.checkbox(
                "Include in AI prompt",
                value=selected_config["include_in_prompt"],  # type: ignore
            )

            # Gitignore settings
            st.subheader("Gitignore Settings")
            use_local_gitignore = st.checkbox(
                "Use local .gitignore patterns (from current directory)",
                value=selected_config.get("use_local_gitignore", True),  # type: ignore
            )
            use_project_gitignore = st.checkbox(
                "Use project .gitignore patterns (from target directory)",
                value=selected_config.get("use_project_gitignore", True),  # type: ignore
            )

            # Ignore patterns management
            st.subheader("Custom Ignore Patterns")
            ignore_patterns = selected_config.get("ignore_patterns", [])  # type: ignore

            # Display current patterns
            if ignore_patterns:
                st.write("Current patterns:")
                for i, pattern in enumerate(ignore_patterns):
                    st.text(f"{i+1}. {pattern}")

            # Add new pattern in the form
            new_pattern = st.text_input("New pattern to add", key="new_pattern")
            
            # Add button to handle adding a pattern when submit is clicked
            if "temp_patterns" not in st.session_state:
                st.session_state.temp_patterns = ignore_patterns.copy()
                
            # Add a placeholder for managing patterns
            patterns_to_remove = []
            if ignore_patterns:
                st.write("Select patterns to remove:")
                for i, pattern in enumerate(ignore_patterns):
                    if st.checkbox(pattern, key=f"remove_pattern_{i}"):
                        patterns_to_remove.append(i)
                    
            # Submit button for the form
            submit = st.form_submit_button("Save Configuration")
            
            if submit:
                # Process pattern changes first
                # Add new pattern if provided
                updated_patterns = ignore_patterns.copy()
                if new_pattern and new_pattern not in updated_patterns:
                    updated_patterns.append(new_pattern)
                
                # Remove selected patterns in reverse order to maintain indices
                for i in sorted(patterns_to_remove, reverse=True):
                    updated_patterns.pop(i)
                
                # Create the new configuration
                new_config = {  # type: ignore
                    "project_name": sanitize_filename(project_name),
                    "directory": root_directory,
                    "output_pattern": output_pattern,
                    "include_in_prompt": include_in_prompt,
                    "use_local_gitignore": use_local_gitignore,
                    "use_project_gitignore": use_project_gitignore,
                    "ignore_patterns": updated_patterns,
                    "last_used": datetime.now().strftime("%Y-%m-%d"),
                }
                assert is_valid_project_config(new_config)
                new_config = cast(ProjectConfig, new_config)

                if action == "Edit":
                    config["configurations"][  # type: ignore
                        config["configurations"].index(selected_config)  # type: ignore
                    ] = new_config
                else:
                    if (
                        len(
                            [
                                c
                                for c in config["configurations"]  # type: ignore
                                if c["directory"] == root_directory
                            ]
                        )
                        >= MAX_CONFIGS_PER_PROJECT
                    ):
                        st.warning(
                            f"Maximum configurations ({MAX_CONFIGS_PER_PROJECT}) reached. Replacing oldest."
                        )
                        config["configurations"] = [  # type: ignore
                            c
                            for c in config["configurations"]  # type: ignore
                            if c["directory"] != root_directory
                        ] + [new_config]
                    else:
                        config["configurations"].append(new_config)  # type: ignore

                save_config(config)
                st.success("Configuration saved!")
                st.session_state.selected_config = new_config
                st.rerun()

    elif action == "Delete":
        if st.button("Confirm Deletion"):
            config["configurations"].remove(selected_config)
            save_config(config)
            st.success("Configuration deleted!")
            st.rerun()

    # Main content area
    st.header("Generate Project Snapshot")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Project Details")
        st.write(f"**Directory:** {root_directory}")
        if "selected_config" in st.session_state:
            selected_config = st.session_state.selected_config
            st.write(f"**Project Name:** {selected_config['project_name']}")
            st.write(f"**Output Pattern:** {selected_config['output_pattern']}")
            st.write(
                f"**Include in AI Prompt:** {'Yes' if selected_config['include_in_prompt'] else 'No'}"
            )
            st.write(
                f"**Use Local Gitignore:** {'Yes' if selected_config.get('use_local_gitignore', True) else 'No'}"
            )
            st.write(
                f"**Use Project Gitignore:** {'Yes' if selected_config.get('use_project_gitignore', True) else 'No'}"
            )
            if selected_config.get("ignore_patterns"):
                st.write("**Custom Ignore Patterns:**")
                for pattern in selected_config["ignore_patterns"]:
                    st.write(f"- {pattern}")
        else:
            st.write("No configuration selected.")

    with col2:
        st.subheader("Actions")
        if st.button("Generate Snapshot", key="generate_button"):
            try:
                if "selected_config" not in st.session_state:
                    st.error("Please select or create a configuration first.")
                    return

                current_config = st.session_state.selected_config
                output_filename = current_config["output_pattern"].format(
                    time=datetime.now().strftime("%Y-%m-%d-%H%M%S")
                )
                output_path = (
                    Path(__file__).resolve().parent
                    / "output"
                    / current_config["project_name"]
                    / output_filename
                )

                with st.spinner("Generating snapshot..."):
                    result = save_project_contents(
                        Path(root_directory),
                        output_path,
                        current_config["project_name"],
                        current_config["include_in_prompt"],
                        current_config.get("ignore_patterns", []),
                        current_config.get("use_local_gitignore", True),
                        current_config.get("use_project_gitignore", True),
                        current_config.get("use_parallel_processing", True),
                        None,  # Use default max_workers
                        current_config.get("check_binary_content", True),
                    )

                st.success(
                    f"Snapshot generated! Processed: {result['processed']}, Skipped: {result['skipped']}"
                )
                if result["errors"]:
                    st.warning("Some errors occurred:")
                    for error in result["errors"]:
                        st.write(f"- {error}")

                if st.button("Copy Output Path"):
                    copy_to_clipboard(str(output_path))
                    st.info("Path copied to clipboard!")

            except Exception as e:
                st.error(f"Error generating snapshot: {str(e)}")
                logger.exception("Error in snapshot generation")


if __name__ == "__main__":
    main()
