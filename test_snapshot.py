import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from datetime import datetime, timedelta
import json
import logging
import main
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


class TestSnapshotFunctions(unittest.TestCase):
    def setUp(self):
        # Suppress Rich console output during tests
        self.original_console = main.console
        main.console = MagicMock()

        # Set up global patches
        self.mock_confirm_patcher = patch("rich.prompt.Confirm.ask")
        self.mock_prompt_patcher = patch("rich.prompt.Prompt.ask")
        self.mock_confirm = self.mock_confirm_patcher.start()
        self.mock_prompt = self.mock_prompt_patcher.start()

        # Set default return values
        self.mock_confirm.return_value = False
        self.mock_prompt.return_value = "1"

        # Set up a logger for the tests
        self.logger = logging.getLogger("test_logger")
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def tearDown(self):
        # Restore the original console
        main.console = self.original_console

        # Stop global patches
        self.mock_confirm_patcher.stop()
        self.mock_prompt_patcher.stop()

    def create_mock_config(self, project_name, include_in_prompt=True):
        return {
            "project_name": project_name,
            "directory": "/fake/path",
            "output_pattern": f"{project_name}-{{time}}.md",
            "include_in_prompt": include_in_prompt,
            "last_used": datetime.now().strftime("%Y-%m-%d"),
        }

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

    def test_load_config_file_not_found(self):
        with patch("pathlib.Path.exists", return_value=False):
            config = main.load_config()
        self.assertEqual(config, {"configurations": []})

    @patch("builtins.open", new_callable=mock_open)
    def test_save_config(self, mock_file):
        config = {"configurations": [{"name": "test"}]}
        main.save_config(config)
        mock_file.assert_called_once_with(main.CONFIG_FILE, "w")
        handle = mock_file()
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)
        expected_content = json.dumps(config, indent=4)
        self.assertEqual(written_content, expected_content)

    def test_create_or_edit_configuration(self):
        root_directory = Path("/fake/root")
        self.mock_confirm.side_effect = [True, True, True]
        result = main.create_or_edit_configuration(root_directory)
        self.assertEqual(result["project_name"], "root")
        self.assertEqual(result["output_pattern"], "root_contents-{time}.md")
        self.assertTrue(result["include_in_prompt"])

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
        self.assertEqual(main.get_user_choice(0), "1")
        self.mock_prompt.return_value = "1"
        self.assertEqual(main.get_user_choice(1), "1")
        self.mock_prompt.return_value = "2"
        self.assertEqual(main.get_user_choice(3), "2")

    @patch("pathlib.Path.is_dir")
    def test_get_target_directory(self, mock_is_dir):
        config = {"last_directory": "/fake/path"}
        self.mock_confirm.return_value = False
        result = main.get_target_directory(config)
        self.assertEqual(result, Path("/fake/path"))

        self.mock_confirm.return_value = True
        self.mock_prompt.return_value = "/new/path"
        mock_is_dir.return_value = True
        result = main.get_target_directory(config)
        self.assertEqual(result, Path("/new/path"))

        self.mock_prompt.side_effect = ["/invalid/path", "/valid/path"]
        mock_is_dir.side_effect = [False, True]
        result = main.get_target_directory(config)
        self.assertEqual(result, Path("/valid/path"))

    def test_is_duplicate_config(self):
        existing_configs = [
            self.create_mock_config("test1"),
            self.create_mock_config("test2", include_in_prompt=False),
        ]

        duplicate_config = self.create_mock_config("test1")
        self.assertTrue(main.is_duplicate_config(duplicate_config, existing_configs))

        new_config = self.create_mock_config("test3")
        self.assertFalse(main.is_duplicate_config(new_config, existing_configs))

    def test_add_configuration(self):
        config = {"configurations": []}
        new_config = self.create_mock_config("test")

        main.add_configuration(config, new_config)
        self.assertEqual(len(config["configurations"]), 1)
        self.assertEqual(config["configurations"][0], new_config)

    def test_add_configuration_max_limit(self):
        config = {"configurations": []}
        for i in range(main.MAX_CONFIGS_PER_PROJECT + 2):
            new_config = self.create_mock_config(f"test{i}")
            main.add_configuration(config, new_config)

        self.assertEqual(len(config["configurations"]), main.MAX_CONFIGS_PER_PROJECT)
        self.assertEqual(
            config["configurations"][-1]["project_name"],
            f"test{main.MAX_CONFIGS_PER_PROJECT + 1}",
        )

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
    ):
        initial_config = {
            "configurations": [
                self.create_mock_config("project1"),
                self.create_mock_config("project2", include_in_prompt=False),
            ]
        }

        mock_load_config.return_value = initial_config.copy()
        mock_get_target.return_value = Path("/fake/path")
        mock_get_choice.side_effect = [
            "3",  # Delete
            "2",  # Choose second config
            "1",  # Use remaining config
        ]
        mock_save_contents.return_value = {"processed": 1, "skipped": 0, "errors": []}

        main.main()

        mock_save_config.assert_called()
        saved_config = mock_save_config.call_args[0][0]

        self.assertEqual(
            len(saved_config["configurations"]),
            1,
            "Configuration was not deleted correctly",
        )
        self.assertEqual(
            saved_config["configurations"][0]["project_name"],
            "project1",
            "Wrong configuration was deleted",
        )

        # Simulate running main again with the updated configuration
        mock_load_config.reset_mock()
        mock_load_config.return_value = saved_config
        mock_get_choice.side_effect = ["1"]  # Use the remaining config

        main.main()

        mock_save_config.assert_called()
        final_config = mock_save_config.call_args[0][0]

        self.assertEqual(
            len(final_config["configurations"]),
            1,
            "Final configuration count is incorrect",
        )
        self.assertEqual(
            final_config["configurations"][0]["project_name"],
            "project1",
            "Final configuration is incorrect",
        )

    @patch("main.get_user_choice")
    @patch("main.get_target_directory")
    @patch("main.load_config")
    @patch("main.save_config")
    @patch("main.save_project_contents")
    def test_main_create_new_config(
        self,
        mock_save_contents,
        mock_save_config,
        mock_load_config,
        mock_get_target,
        mock_get_choice,
    ):
        initial_config = {"configurations": []}

        mock_load_config.return_value = initial_config.copy()
        mock_get_target.return_value = Path("/fake/path")
        mock_get_choice.side_effect = ["1"]  # Create new configuration
        self.mock_confirm.side_effect = [
            True,
            True,
            True,
            False,
        ]  # Use defaults for new config, don't copy to clipboard
        mock_save_contents.return_value = {"processed": 1, "skipped": 0, "errors": []}

        main.main()

        mock_save_config.assert_called()
        saved_config = mock_save_config.call_args[0][0]

        self.assertEqual(
            len(saved_config["configurations"]),
            1,
            "New configuration was not created correctly",
        )
        self.assertEqual(
            saved_config["configurations"][0]["project_name"],
            "path",
            "Wrong project name for new configuration",
        )

    @patch("snapshot.capture.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    @patch("snapshot.capture.load_gitignore_patterns")
    @patch("snapshot.capture.os.walk")
    @patch("snapshot.capture.read_file_content")
    def test_save_project_contents(
        self, mock_read_content, mock_walk, mock_load_patterns, mock_file, mock_mkdir
    ):
        root_directory = Path("/fake/root")
        output_path = Path("/fake/output/project_contents.md")
        project_name = "test_project"
        include_in_prompt = True

        mock_load_patterns.return_value.match_file.return_value = False
        mock_walk.return_value = [
            ("/fake/root", ["dir1"], ["file1.txt", "file2.py"]),
            ("/fake/root/dir1", [], ["file3.md"]),
        ]
        mock_read_content.return_value = "File content"

        result = save_project_contents(
            root_directory, output_path, project_name, include_in_prompt
        )

        self.assertEqual(result["processed"], 3)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["errors"], [])

        mock_mkdir.assert_called()
        mock_file.assert_called_with(output_path, "w")
        handle = mock_file()
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)
        self.assertIn("# Project Snapshot: test_project", written_content)
        self.assertIn("## Directory Tree", written_content)
        self.assertIn("## File Contents", written_content)
        self.assertIn("### file1.txt", written_content)
        self.assertIn("### file2.py", written_content)
        self.assertIn("### dir1/file3.md", written_content)

    @patch("snapshot.capture.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    @patch("snapshot.capture.load_gitignore_patterns")
    @patch("snapshot.capture.os.walk")
    @patch("snapshot.capture.read_file_content")
    def test_save_project_contents_with_errors(
        self, mock_read_content, mock_walk, mock_load_patterns, mock_file, mock_mkdir
    ):
        root_directory = Path("/fake/root")
        output_path = Path("/fake/output/project_contents.md")
        project_name = "test_project"
        include_in_prompt = True

        mock_load_patterns.return_value.match_file.return_value = False
        mock_walk.return_value = [("/fake/root", [], ["file1.txt", "file2.bin"])]
        mock_read_content.side_effect = [
            "File content",
            ProjectSnapshotError("Binary file"),
        ]

        result = save_project_contents(
            root_directory, output_path, project_name, include_in_prompt
        )

        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(len(result["errors"]), 1)

        mock_mkdir.assert_called()
        mock_file.assert_called_with(output_path, "w")
        handle = mock_file()
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)
        self.assertIn("# Project Snapshot: test_project", written_content)
        self.assertIn("## Directory Tree", written_content)
        self.assertIn("## File Contents", written_content)
        self.assertIn("### file1.txt", written_content)
        self.assertIn("### file2.bin", written_content)
        self.assertIn("File content not displayed due to an error", written_content)

    @patch("main.get_user_choice")
    @patch("main.get_target_directory")
    @patch("main.load_config")
    @patch("main.save_config")
    @patch("main.save_project_contents")
    @patch("main.copy_to_clipboard")
    def test_main_integration(
        self,
        mock_copy_to_clipboard,
        mock_save_contents,
        mock_save_config,
        mock_load_config,
        mock_get_target,
        mock_get_choice,
    ):
        initial_config = {
            "configurations": [
                self.create_mock_config("project1"),
                self.create_mock_config("project2", include_in_prompt=False),
            ]
        }

        mock_load_config.return_value = initial_config.copy()
        mock_get_target.return_value = Path("/fake/path")
        mock_get_choice.side_effect = ["1"]  # Use existing configuration
        mock_save_contents.return_value = {"processed": 10, "skipped": 2, "errors": []}
        mock_copy_to_clipboard.return_value = True
        self.mock_confirm.side_effect = [True]  # Copy to clipboard

        with patch("main.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2023-07-25-120000"
            main.main()

        mock_save_config.assert_called()
        mock_save_contents.assert_called_with(
            Path("/fake/path"),
            Path("/fake/path/output/project1/project1-2023-07-25-120000.md"),
            "project1",
            True,
        )
        mock_copy_to_clipboard.assert_called()

    def test_delete_configuration(self):
        config = {
            "configurations": [
                self.create_mock_config("project1"),
                self.create_mock_config("project2"),
            ]
        }
        main.delete_configuration(config, 0)
        self.assertEqual(len(config["configurations"]), 1)
        self.assertEqual(config["configurations"][0]["project_name"], "project2")

    def test_edit_configuration(self):
        config = {
            "configurations": [
                self.create_mock_config("project1"),
                self.create_mock_config("project2"),
            ]
        }
        new_config = self.create_mock_config("edited_project")
        main.edit_configuration(config, 0, new_config)
        self.assertEqual(config["configurations"][0]["project_name"], "edited_project")


if __name__ == "__main__":
    unittest.main()
