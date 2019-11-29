import os
import sys
import logging
import unittest

logger = logging.getLogger(__name__)


class FormattingTestCase(unittest.TestCase):
    def test_formatting_black(self):
        project_path = os.path.join(os.path.dirname(__file__), "../..")
        latigo_path = os.path.join(project_path, "app")
        tests_path = os.path.join(project_path, "tests")
        parts = [sys.executable, "-m", "black", "-l", "999", "-t", "py37", "--check", "-v", latigo_path, tests_path, "--exclude", r".*_version.py", "--exclude", r".eggs"]
        cmd = " ".join(parts)
        # logger.warning(f"Running: {cmd}")
        exit_code = os.system(cmd)
        self.assertEqual(exit_code, 0)
