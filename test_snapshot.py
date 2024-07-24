import unittest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from snapshot.capture import load_gitignore_patterns, get_language, escape_markdown, read_file_content, save_project_contents
from snapshot.exceptions import ProjectSnapshotError
from snapshot.utils import copy_to_clipboard, sanitize_path

class TestSnapshotFunctions(unittest.TestCase):

    def test_load_gitignore_patterns(self):
        mock_gitignore_content = "*.pyc\n__pycache__\n"
        with patch("pathlib.Path.open", mock_open(read_data=mock_gitignore_content)):
            with patch("pathlib.Path.exists", return_value=True):
                patterns = load_gitignore_patterns(Path("/fake/path"))
        self.assertTrue(patterns.match_file("test.pyc"))
        self.assertTrue(patterns.match_file("__pycache__"))
        self.assertFalse(patterns.match_file("test.py"))

    def test_get_language(self):
        self.assertEqual(get_language('.py'), 'python')
        self.assertEqual(get_language('.js'), 'javascript')
        self.assertEqual(get_language('.unknown'), '')

    def test_escape_markdown(self):
        test_string = "This is a *test* with [markdown](syntax)"
        expected = "This is a \\*test\\* with \\[markdown\\]\\(syntax\\)"
        self.assertEqual(escape_markdown(test_string), expected)

    @patch('snapshot.capture.mmap.mmap')
    def test_read_file_content_large_file(self, mock_mmap):
        mock_mmap.return_value.__enter__.return_value.read.return_value = b'Large file content'
        with patch('snapshot.capture.Path.stat') as mock_stat:
            mock_stat.return_value.st_size = 2_000_000
            content = read_file_content(Path('large_file.txt'))
        self.assertEqual(content, 'Large file content')

    def test_read_file_content_small_file(self):
        with patch('snapshot.capture.Path.read_text', return_value='Small file content'):
            with patch('snapshot.capture.Path.stat') as mock_stat:
                mock_stat.return_value.st_size = 500_000
                content = read_file_content(Path('small_file.txt'))
        self.assertEqual(content, 'Small file content')

    def test_read_file_content_error(self):
        with patch('snapshot.capture.Path.stat', side_effect=IOError("Test error")):
            with self.assertRaises(ProjectSnapshotError):
                read_file_content(Path('error_file.txt'))

    @patch('snapshot.capture.load_gitignore_patterns')
    @patch('snapshot.capture.read_file_content')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_project_contents(self, mock_file, mock_read_content, mock_load_patterns):
        mock_load_patterns.return_value = MagicMock()
        mock_read_content.return_value = "File content"
        root_dir = Path("/fake/root")
        output_file = Path("/fake/output.md")
        project_name = "Test Project"
        
        save_project_contents(root_dir, output_file, project_name, include_in_prompt=False)
        
        mock_file.assert_called_with(output_file, 'w')
        handle = mock_file()
        handle.write.assert_called()

    def test_copy_to_clipboard(self):
        with patch('pyperclip.copy') as mock_copy:
            result = copy_to_clipboard("Test text")
            self.assertTrue(result)
            mock_copy.assert_called_with("Test text")

    def test_sanitize_path_valid(self):
        with patch('pathlib.Path.cwd', return_value=Path("/fake/cwd")):
            result = sanitize_path("/fake/cwd/test/path")
            self.assertEqual(result, Path("/fake/cwd/test/path"))

    def test_sanitize_path_invalid(self):
        with patch('pathlib.Path.cwd', return_value=Path("/fake/cwd")):
            with self.assertRaises(ValueError):
                sanitize_path("/fake/outside/path")

if __name__ == '__main__':
    unittest.main()