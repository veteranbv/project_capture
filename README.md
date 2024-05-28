# Project Snapshot Tool

This tool captures the contents of a project directory, excluding build artifacts, dependencies, and ignored files, and generates a detailed snapshot of the project's files for analysis or documentation purposes.

## Features

- Honors `.gitignore` patterns
- Excludes common build directories and dependencies
- Generates a directory tree and captures file contents
- Configurable via environment variables

## Project Structure

```zsh
project-snapshot/
├── .env
├── .gitignore
├── README.md
├── requirements.txt
├── snapshot/
│   ├── __init__.py
│   ├── capture.py
│   ├── utils.py
└── main.py
```

## Setup

1. Clone the repository:

   ```sh
   git clone <repository_url>
   cd project-snapshot
   ```

2. Create and activate a virtual environment:

   ```sh
   python3 -m venv venv
   source venv/bin/activate   # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required dependencies:

   ```sh
   pip install -r requirements.txt
   ```

4. Configure the target directory in the `.env` file:

   ```env
   DIRECTORY=your_project_directory
   ```

## Usage

Run the script to generate the project snapshot:

```sh
python3 main.py
```

The output will be saved in the `./output` directory.

## License

MIT License
