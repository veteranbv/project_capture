import unittest
import json
import os
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime, timedelta
from rich.console import Console
from snapshot.capture import (
    load_gitignore_patterns,
    get_language,
    escape_markdown,
    read_file_content,
    save_project_contents,
    is_binary_file,
)
from snapshot.exceptions import ProjectSnapshotError
from snapshot.utils import copy_to_clipboard, sanitize_filename
import main


class TestSnapshotFunctions(unittest.TestCase):
    def setUp(self):
        # Suppress Rich console output during tests
        self.original_console = main.console
        self.null_file = open(os.devnull, "w")
        main.console = Console(file=self.null_file)

        # Set up global patches
        self.mock_confirm_patcher = patch("rich.prompt.Confirm.ask")
        self.mock_prompt_patcher = patch("rich.prompt.Prompt.ask")
        self.mock_confirm = self.mock_confirm_patcher.start()
        self.mock_prompt = self.mock_prompt_patcher.start()

        # Set default return values
        self.mock_confirm.return_value = False
        self.mock_prompt.return_value = "1"

    def tearDown(self):
        # Restore the original console and close the null file
        main.console = self.original_console
        self.null_file.close()

        # Stop global patches
        self.mock_confirm_patcher.stop()
        self.mock_prompt_patcher.stop()

    def test_load_gitignore_patterns(self):
        mock_gitignore_content = "*.pyc\n__pycache__\n"
        with patch("pathlib.Path.open", mock_open(read_data=mock_gitignore_content)):
            with patch("pathlib.Path.exists", return_value=True):
                patterns = load_gitignore_patterns(Path("/fake/path"))
        self.assertTrue(patterns.match_file("test.pyc"))
        self.assertTrue(patterns.match_file("__pycache__"))
        self.assertFalse(patterns.match_file("test.py"))

    def test_get_language(self):
        self.assertEqual(get_language(".py"), "python")
        self.assertEqual(get_language(".js"), "javascript")
        self.assertEqual(get_language(".unknown"), "")

    def test_escape_markdown(self):
        test_string = "This is a *test* with [markdown](syntax)"
        expected = "This is a \\*test\\* with \\[markdown\\]\\(syntax\\)"
        self.assertEqual(escape_markdown(test_string), expected)

    @patch("snapshot.capture.mmap.mmap")
    @patch("snapshot.capture.Path.open")
    @patch("snapshot.capture.Path.stat")
    def test_read_file_content_large_file(self, mock_stat, mock_open, mock_mmap):
        mock_stat.return_value.st_size = 2_000_000
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        mock_mmap.return_value.__enter__.return_value.read.return_value = (
            b"Large file content"
        )

        content = read_file_content(Path("large_file.txt"))

        self.assertEqual(content, "Large file content")
        mock_open.assert_called_once_with("rb")
        mock_mmap.assert_called_once()

    def test_read_file_content_small_file(self):
        with patch(
            "snapshot.capture.Path.read_text", return_value="Small file content"
        ):
            with patch("snapshot.capture.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = 500_000
                content = read_file_content(Path("small_file.txt"))
        self.assertEqual(content, "Small file content")

    def test_read_file_content_binary_file(self):
        with patch("snapshot.capture.is_binary_file", return_value=True):
            with self.assertRaises(ProjectSnapshotError):
                read_file_content(Path("binary_file.exe"))

    @patch("snapshot.capture.load_gitignore_patterns")
    @patch("snapshot.capture.read_file_content")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    def test_save_project_contents(
        self, mock_mkdir, mock_file, mock_read_content, mock_load_patterns
    ):
        mock_load_patterns.return_value = MagicMock()
        mock_read_content.return_value = "File content"
        root_dir = Path("/fake/root")
        output_file = Path("/fake/output/test.md")
        project_name = "Test Project"

        result = save_project_contents(
            root_dir, output_file, project_name, include_in_prompt=False
        )

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file.assert_called_with(output_file, "w")
        handle = mock_file()
        handle.write.assert_called()
        self.assertIsInstance(result, dict)
        self.assertIn("processed", result)
        self.assertIn("skipped", result)
        self.assertIn("errors", result)

    def test_is_binary_file(self):
        self.assertTrue(is_binary_file(Path("test.jpg")))
        self.assertTrue(is_binary_file(Path("test.exe")))
        self.assertFalse(is_binary_file(Path("test.txt")))
        self.assertFalse(is_binary_file(Path("test.py")))

    @patch("pyperclip.copy")
    def test_copy_to_clipboard(self, mock_copy):
        result = copy_to_clipboard("Test text")
        self.assertTrue(result)
        mock_copy.assert_called_with("Test text")

    @patch("builtins.open", new_callable=mock_open, read_data='{"configurations": []}')
    def test_load_config(self, mock_file):
        with patch("pathlib.Path.exists", return_value=True):
            config = main.load_config()
        self.assertIn("configurations", config)
        self.assertEqual(config["configurations"], [])

    @patch("builtins.open", new_callable=mock_open)
    def test_save_config(self, mock_file):
        config = {"configurations": [{"name": "test"}]}
        main.save_config(config)
        mock_file.assert_called_once_with(main.CONFIG_FILE, "w")
        handle = mock_file()

        # Check if the written content is correct
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)
        expected_content = json.dumps(config, indent=4)
        self.assertEqual(written_content, expected_content)

    def test_create_or_edit_configuration(self):
        root_directory = Path("/fake/root")
        self.mock_confirm.side_effect = [
            True,
            True,
            True,
        ]  # Use default project name, default filename, include in prompt

        result = main.create_or_edit_configuration(root_directory)

        self.assertEqual(result["project_name"], "root")
        self.assertEqual(result["output_pattern"], "root_contents-{time}.md")
        self.assertTrue(result["include_in_prompt"])

        # Test with custom inputs
        self.mock_confirm.side_effect = [False, False, False]
        self.mock_prompt.side_effect = ["custom project", "custom_{time}"]

        result = main.create_or_edit_configuration(root_directory)

        self.assertEqual(result["project_name"], "custom project")
        self.assertEqual(result["output_pattern"], "custom_{time}-{time}.md")
        self.assertFalse(result["include_in_prompt"])

    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename("test.txt"), "test.txt")
        self.assertEqual(sanitize_filename("test/file.txt"), "testfile.txt")
        self.assertEqual(sanitize_filename("test:file.txt"), "testfile.txt")

    def test_get_user_choice(self):
        # Test with no configurations
        self.assertEqual(main.get_user_choice(0), "1")

        # Test with one configuration
        self.mock_prompt.return_value = "1"
        self.assertEqual(main.get_user_choice(1), "1")

        # Test with multiple configurations
        self.mock_prompt.return_value = "2"
        self.assertEqual(main.get_user_choice(3), "2")

    @patch("pathlib.Path.is_dir")
    def test_get_target_directory(self, mock_is_dir):
        config = {"last_directory": "/fake/path"}

        # Test when user doesn't want to update
        self.mock_confirm.return_value = False
        result = main.get_target_directory(config)
        self.assertEqual(result, Path("/fake/path"))

        # Test when user wants to update and provides a valid directory
        self.mock_confirm.return_value = True
        self.mock_prompt.return_value = "/new/path"
        mock_is_dir.return_value = True
        result = main.get_target_directory(config)
        self.assertEqual(result, Path("/new/path"))

        # Test when user provides an invalid directory, then a valid one
        self.mock_prompt.side_effect = ["/invalid/path", "/valid/path"]
        mock_is_dir.side_effect = [False, True]
        result = main.get_target_directory(config)
        self.assertEqual(result, Path("/valid/path"))

    @patch("main.create_or_edit_configuration")
    @patch("main.get_user_choice")
    @patch("main.get_target_directory")
    @patch("main.load_config")
    @patch("main.save_config")
    @patch("main.save_project_contents")
    def test_main_new_config_handling(
        self,
        mock_save_contents,
        mock_save_config,
        mock_load_config,
        mock_get_target,
        mock_get_choice,
        mock_create_config,
    ):
        mock_load_config.return_value = {
            "configurations": [
                {
                    "project_name": "existing_project",
                    "directory": "/fake/path",
                    "output_pattern": "existing_pattern-{time}.md",
                    "include_in_prompt": True,
                    "last_used": "2024-07-23",
                }
            ]
        }
        mock_get_target.return_value = Path("/fake/path")
        mock_get_choice.side_effect = [
            "4",
            "1",
        ]  # Choose to create new configuration, then use it
        mock_create_config.return_value = {
            "project_name": "new_project",
            "directory": "/fake/path",
            "output_pattern": "new_pattern-{time}.md",
            "include_in_prompt": False,
        }
        mock_save_contents.return_value = {"processed": 1, "skipped": 0, "errors": []}
        self.mock_confirm.return_value = False  # Don't copy to clipboard

        main.main()

        mock_save_config.assert_called()
        saved_config = mock_save_config.call_args[0][0]

        self.assertEqual(len(saved_config["configurations"]), 2)
        new_config = saved_config["configurations"][1]
        self.assertEqual(new_config["project_name"], "new_project")
        self.assertEqual(new_config["output_pattern"], "new_pattern-{time}.md")
        self.assertFalse(new_config["include_in_prompt"])
        self.assertIn(
            new_config["last_used"],
            [
                datetime.now().strftime("%Y-%m-%d"),
                (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            ],
        )

    @patch("main.create_or_edit_configuration")
    @patch("main.get_user_choice")
    @patch("main.get_target_directory")
    @patch("main.load_config")
    @patch("main.save_config")
    @patch("main.save_project_contents")
    def test_main_delete_config(
        self,
        mock_save_contents,
        mock_save_config,
        mock_load_config,
        mock_get_target,
        mock_get_choice,
        mock_create_config,
    ):
        mock_load_config.return_value = {
            "configurations": [
                {
                    "project_name": "project1",
                    "directory": "/fake/path",
                    "output_pattern": "pattern1-{time}.md",
                    "include_in_prompt": True,
                    "last_used": "2024-07-23",
                },
                {
                    "project_name": "project2",
                    "directory": "/fake/path",
                    "output_pattern": "pattern2-{time}.md",
                    "include_in_prompt": False,
                    "last_used": "2024-07-24",
                },
            ]
        }
        mock_get_target.return_value = Path("/fake/path")
        mock_get_choice.side_effect = [
            "3",
            "1",
        ]  # Choose to delete, then use remaining config
        self.mock_prompt.side_effect = [
            "1",
            "1",
        ]  # Select first config to delete, then use remaining config
        mock_save_contents.return_value = {"processed": 1, "skipped": 0, "errors": []}
        self.mock_confirm.return_value = False  # Don't copy to clipboard

        main.main()

        mock_save_config.assert_called()
        saved_config = mock_save_config.call_args[0][0]

        self.assertEqual(len(saved_config["configurations"]), 1)
        remaining_config = saved_config["configurations"][0]
        self.assertEqual(remaining_config["project_name"], "project2")
        self.assertEqual(remaining_config["output_pattern"], "pattern2-{time}.md")
        self.assertFalse(remaining_config["include_in_prompt"])
        self.assertIn(
            remaining_config["last_used"],
            [
                datetime.now().strftime("%Y-%m-%d"),
                (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            ],
        )

    @patch("main.create_or_edit_configuration")
    @patch("main.get_user_choice")
    @patch("main.get_target_directory")
    @patch("main.load_config")
    @patch("main.save_config")
    @patch("main.save_project_contents")
    def test_main_edit_config(
        self,
        mock_save_contents,
        mock_save_config,
        mock_load_config,
        mock_get_target,
        mock_get_choice,
        mock_create_config,
    ):
        mock_load_config.return_value = {
            "configurations": [
                {
                    "project_name": "existing_project",
                    "directory": "/fake/path",
                    "output_pattern": "existing_pattern-{time}.md",
                    "include_in_prompt": True,
                    "last_used": "2024-07-23",
                }
            ]
        }
        mock_get_target.return_value = Path("/fake/path")
        mock_get_choice.side_effect = [
            "2",
            "1",
        ]  # Choose to edit, then use the edited config
        self.mock_prompt.return_value = "1"  # Choose the first configuration to edit
        mock_create_config.return_value = {
            "project_name": "edited_project",
            "directory": "/fake/path",
            "output_pattern": "edited_pattern-{time}.md",
            "include_in_prompt": False,
        }
        mock_save_contents.return_value = {"processed": 1, "skipped": 0, "errors": []}
        self.mock_confirm.return_value = False  # Don't copy to clipboard

        main.main()

        mock_save_config.assert_called()
        saved_config = mock_save_config.call_args[0][0]

        self.assertEqual(len(saved_config["configurations"]), 1)
        edited_config = saved_config["configurations"][0]
        self.assertEqual(edited_config["project_name"], "edited_project")
        self.assertEqual(edited_config["output_pattern"], "edited_pattern-{time}.md")
        self.assertFalse(edited_config["include_in_prompt"])
        self.assertIn(
            edited_config["last_used"],
            [
                datetime.now().strftime("%Y-%m-%d"),
                (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            ],
        )

    def test_is_duplicate_config(self):
        existing_configs = [
            {
                "project_name": "test1",
                "directory": "/path/1",
                "output_pattern": "test1_{time}.md",
                "include_in_prompt": True,
            },
            {
                "project_name": "test2",
                "directory": "/path/2",
                "output_pattern": "test2_{time}.md",
                "include_in_prompt": False,
            },
        ]

        # Test duplicate config
        duplicate_config = {
            "project_name": "test1",
            "directory": "/path/1",
            "output_pattern": "test1_{time}.md",
            "include_in_prompt": True,
        }
        self.assertTrue(main.is_duplicate_config(duplicate_config, existing_configs))

        # Test non-duplicate config
        new_config = {
            "project_name": "test3",
            "directory": "/path/3",
            "output_pattern": "test3_{time}.md",
            "include_in_prompt": True,
        }
        self.assertFalse(main.is_duplicate_config(new_config, existing_configs))

    def test_add_configuration(self):
        config = {"configurations": []}
        new_config = {
            "project_name": "test",
            "directory": "/path/test",
            "output_pattern": "test_{time}.md",
            "include_in_prompt": True,
            "last_used": datetime.now().strftime("%Y-%m-%d"),
        }

        # Test adding a new configuration
        main.add_configuration(config, new_config)
        self.assertEqual(len(config["configurations"]), 1)
        self.assertEqual(config["configurations"][0], new_config)

        # Test FIFO behavior
        for i in range(1, main.MAX_CONFIGS_PER_PROJECT + 1):
            new_config = {
                "project_name": f"test{i}",
                "directory": "/path/test",
                "output_pattern": f"test{i}_{{time}}.md",
                "include_in_prompt": True,
                "last_used": datetime.now().strftime("%Y-%m-%d"),
            }
            main.add_configuration(config, new_config)

        self.assertEqual(len(config["configurations"]), main.MAX_CONFIGS_PER_PROJECT)
        self.assertEqual(
            config["configurations"][-1]["project_name"],
            f"test{main.MAX_CONFIGS_PER_PROJECT}",
        )


if __name__ == "__main__":
    unittest.main()
