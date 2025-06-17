Getting Started
===============

Installation
------------

Quick Setup
^^^^^^^^^^^

Use the provided setup script for a complete development environment::

    git clone <repository_url>
    cd project-capture
    ./setup.sh

This will:

- Create a virtual environment
- Install all dependencies
- Set up pre-commit hooks
- Create necessary directories

Manual Installation
^^^^^^^^^^^^^^^^^^^

1. Clone the repository::

    git clone <repository_url>
    cd project-capture

2. Create and activate a virtual environment::

    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install the package::

    pip install -e ".[dev]"

Quick Start
-----------

CLI Usage
^^^^^^^^^

Run the command-line interface::

    ./project_capture

Or use Python module syntax::

    python -m project_capture.cli

Web Interface
^^^^^^^^^^^^^

Launch the Streamlit web interface::

    streamlit run src/project_capture/web/app.py

Or use the Makefile::

    make run-web

Programmatic Usage
^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from pathlib import Path
    from project_capture import capture_project_contents
    
    result = capture_project_contents(
        root_directory=Path("."),
        output_filename=Path("output/snapshot.md"),
        project_name="My Project",
        include_in_prompt=False,
    )
    
    print(f"Captured {result['processed']} files")
    print(f"Output: {result['output_path']}")

Next Steps
----------

- Read the :doc:`architecture/overview` to understand the system design
- Check :doc:`guides/migration` if upgrading from v0.1.x
- Review :doc:`guides/coding-standards` for development guidelines
- See the :doc:`api/index` for detailed API documentation