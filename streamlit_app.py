import streamlit as st
import sys
import json
from pathlib import Path
from datetime import datetime
import logging
from snapshot.capture import save_project_contents
from snapshot.exceptions import ProjectSnapshotError
from snapshot.utils import copy_to_clipboard, configure_logging, sanitize_filename

# Configure logging
logger = configure_logging()

CONFIG_FILE = "config.json"
MAX_CONFIGS_PER_PROJECT = 5

# Load config
@st.cache_data
def load_config():
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

# Save config
def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
    except IOError as e:
        logger.error(f"Error writing to {CONFIG_FILE}: {str(e)}")

def get_subdirectories(path):
    return [d for d in Path(path).iterdir() if d.is_dir()]

def main():
    st.set_page_config(page_title="Project Snapshot", page_icon="📸", layout="wide")
    
    st.title("📸 Project Snapshot")
    st.subheader("AI-Ready Project Capture Tool")
    
    # Sidebar for configuration management
    with st.sidebar:
        st.header("Configuration")
        config = load_config()
        
        # Directory selection
        st.subheader("1. Select Project Directory")
        
        # Use session state to store the selected directory
        if "root_directory" not in st.session_state:
            st.session_state.root_directory = config.get("last_directory", str(Path.cwd()))

        current_path = Path(st.session_state.root_directory)
        st.write(f"Current directory: {current_path}")

        # Go up one level
        if current_path != current_path.root:
            if st.button("⬆️ Up one level"):
                st.session_state.root_directory = str(current_path.parent)
                st.rerun()  # Changed from st.experimental_rerun()

        # List subdirectories
        subdirs = get_subdirectories(current_path)
        if subdirs:
            selected_subdir = st.selectbox("Select subdirectory", [""] + [d.name for d in subdirs])
            if selected_subdir:
                st.session_state.root_directory = str(current_path / selected_subdir)
                st.rerun()  # Changed from st.experimental_rerun()

        # Manual input
        root_directory = st.text_input("Or enter path manually", value=st.session_state.root_directory, key="directory_input")
        
        if not Path(root_directory).is_dir():
            st.error("Invalid directory. Please select a valid directory or enter a valid path.")
            return
        
        # Update the last_directory in config
        config["last_directory"] = root_directory
        save_config(config)

        # Configuration management
        st.subheader("2. Manage Configurations")
        matching_configs = [c for c in config["configurations"] if c["directory"] == root_directory]
        
        if matching_configs:
            selected_config = st.selectbox(
                "Select Configuration",
                options=matching_configs,
                format_func=lambda x: x['project_name'],
                key="config_select"
            )
            
            action = st.radio("Action", ["Use Selected", "Edit", "Delete", "Create New"])
        else:
            st.info("No existing configurations found for this directory.")
            action = "Create New"
        
        if action in ["Edit", "Create New"]:
            st.subheader("3. Configure Snapshot")
            project_name = st.text_input("Project Name", value=selected_config['project_name'] if action == "Edit" else Path(root_directory).name)
            output_pattern = st.text_input("Output Pattern", value=selected_config['output_pattern'] if action == "Edit" else f"{project_name}_contents-{{time}}.md")
            include_in_prompt = st.checkbox("Include in AI prompt", value=selected_config['include_in_prompt'] if action == "Edit" else True)
            
            if st.button("Save Configuration"):
                new_config = {
                    "project_name": sanitize_filename(project_name),
                    "directory": root_directory,
                    "output_pattern": output_pattern,
                    "include_in_prompt": include_in_prompt,
                    "last_used": datetime.now().strftime("%Y-%m-%d"),
                }
                
                if action == "Edit":
                    config["configurations"][config["configurations"].index(selected_config)] = new_config
                else:
                    if len([c for c in config["configurations"] if c["directory"] == root_directory]) >= MAX_CONFIGS_PER_PROJECT:
                        st.warning(f"Maximum configurations ({MAX_CONFIGS_PER_PROJECT}) reached. Replacing oldest.")
                        config["configurations"] = [c for c in config["configurations"] if c["directory"] != root_directory] + [new_config]
                    else:
                        config["configurations"].append(new_config)
                
                save_config(config)
                st.success("Configuration saved!")
                st.rerun()  # Changed from st.experimental_rerun()
        
        elif action == "Delete":
            if st.button("Confirm Deletion"):
                config["configurations"].remove(selected_config)
                save_config(config)
                st.success("Configuration deleted!")
                st.rerun()  # Changed from st.experimental_rerun()
    
    # Main content area
    st.header("Generate Project Snapshot")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Project Details")
        st.write(f"**Directory:** {root_directory}")
        if 'selected_config' in locals():
            st.write(f"**Project Name:** {selected_config['project_name']}")
            st.write(f"**Output Pattern:** {selected_config['output_pattern']}")
            st.write(f"**Include in AI Prompt:** {'Yes' if selected_config['include_in_prompt'] else 'No'}")
    
    with col2:
        st.subheader("Actions")
        if st.button("Generate Snapshot", key="generate_button"):
            try:
                if 'selected_config' not in locals():
                    st.error("Please select or create a configuration first.")
                    return
                
                output_filename = selected_config["output_pattern"].format(time=datetime.now().strftime("%Y-%m-%d-%H%M%S"))
                output_path = Path(__file__).resolve().parent / "output" / selected_config["project_name"] / output_filename
                
                with st.spinner("Generating snapshot..."):
                    result = save_project_contents(
                        Path(root_directory),
                        output_path,
                        selected_config["project_name"],
                        selected_config["include_in_prompt"],
                    )
                
                st.success("Snapshot generated successfully!")
                
                # Display results
                st.subheader("Snapshot Results")
                st.write(f"**Output File:** {output_path}")
                st.write(f"**Processed Files:** {result['processed']}")
                st.write(f"**Skipped Files:** {result['skipped']}")
                st.write(f"**Errors:** {len(result['errors'])}")
                
                if result['errors']:
                    with st.expander("View Errors"):
                        for error in result['errors']:
                            st.write(error)
                
                if st.button("Copy Output Path"):
                    if copy_to_clipboard(str(output_path)):
                        st.success("Output path copied to clipboard.")
                    else:
                        st.warning("Failed to copy. Please copy the path manually.")
                
                # Option to view snapshot content
                if st.button("View Snapshot Content"):
                    with open(output_path, 'r') as file:
                        st.code(file.read())
                
            except ProjectSnapshotError as e:
                st.error(f"Error generating snapshot: {str(e)}")
            except Exception as e:
                st.error(f"Unexpected error: {str(e)}")
                logger.exception("An unexpected error occurred")

    # Help and Documentation
    with st.expander("Help & Documentation"):
        st.markdown("""
        ### How to use Project Snapshot:
        1. **Select Project Directory**: Use the directory navigation to choose your project's root directory, or enter the full path manually.
        2. **Manage Configurations**: Select an existing configuration or create a new one.
        3. **Generate Snapshot**: Click the 'Generate Snapshot' button to create a comprehensive snapshot of your project.
        4. **View Results**: After generation, you can view the results, copy the output path, or view the snapshot content.

        ### Tips:
        - Use meaningful project names and output patterns for easy identification.
        - The 'Include in AI Prompt' option wraps the snapshot in a format optimized for AI consumption.
        - Review any errors or skipped files to ensure all necessary content is captured.
        """)

if __name__ == "__main__":
    main()