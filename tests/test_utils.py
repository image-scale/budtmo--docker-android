import os
import pytest
from unittest import TestCase

from android_runner.utils import str_to_bool, require_env, create_symlink


class TestStrToBool(TestCase):
    def test_truthy_values(self):
        self.assertTrue(str_to_bool("true"))
        self.assertTrue(str_to_bool("TRUE"))
        self.assertTrue(str_to_bool("True"))
        self.assertTrue(str_to_bool("yes"))
        self.assertTrue(str_to_bool("Yes"))
        self.assertTrue(str_to_bool("YES"))
        self.assertTrue(str_to_bool("t"))
        self.assertTrue(str_to_bool("T"))
        self.assertTrue(str_to_bool("1"))

    def test_falsy_values(self):
        self.assertFalse(str_to_bool("false"))
        self.assertFalse(str_to_bool("False"))
        self.assertFalse(str_to_bool("FALSE"))
        self.assertFalse(str_to_bool("no"))
        self.assertFalse(str_to_bool("f"))
        self.assertFalse(str_to_bool("0"))
        self.assertFalse(str_to_bool("random"))

    def test_empty_values(self):
        self.assertFalse(str_to_bool(None))
        self.assertFalse(str_to_bool(""))

    def test_whitespace_value(self):
        self.assertFalse(str_to_bool(" "))
        self.assertFalse(str_to_bool("   "))

    def test_non_string_raises_error(self):
        with self.assertRaises(AttributeError):
            str_to_bool(True)
        with self.assertRaises(AttributeError):
            str_to_bool(1)
        with self.assertRaises(AttributeError):
            str_to_bool(0)


class TestRequireEnv(TestCase):
    def setUp(self):
        self.test_keys = []

    def tearDown(self):
        for key in self.test_keys:
            if key in os.environ:
                del os.environ[key]

    def test_returns_value_when_set(self):
        key = "TEST_REQUIRE_ENV_VALUE"
        self.test_keys.append(key)
        os.environ[key] = "my_test_value"
        result = require_env(key)
        self.assertEqual(result, "my_test_value")

    def test_raises_when_missing(self):
        key = "TEST_MISSING_ENV_VAR_DOES_NOT_EXIST"
        with self.assertRaises(RuntimeError) as ctx:
            require_env(key)
        self.assertIn(key, str(ctx.exception))

    def test_raises_when_whitespace_only(self):
        key = "TEST_WHITESPACE_ENV_VAR"
        self.test_keys.append(key)
        os.environ[key] = "    "
        with self.assertRaises(RuntimeError) as ctx:
            require_env(key)
        self.assertIn("white space", str(ctx.exception))


class TestCreateSymlink(TestCase):
    def setUp(self):
        self.test_files = []

    def tearDown(self):
        for path in self.test_files:
            if os.path.islink(path) or os.path.isfile(path):
                os.remove(path)

    def test_creates_symlink(self):
        source = "test_source_file.txt"
        target = "test_target_link.txt"
        self.test_files.extend([source, target])

        with open(source, "w") as f:
            f.write("test content")

        create_symlink(source, target)

        self.assertTrue(os.path.islink(target))
        self.assertEqual(os.readlink(target), source)

    def test_replaces_existing_file(self):
        source = "test_source_replace.txt"
        target = "test_target_replace.txt"
        self.test_files.extend([source, target])

        with open(source, "w") as f:
            f.write("source content")
        with open(target, "w") as f:
            f.write("existing content")

        create_symlink(source, target)

        self.assertTrue(os.path.islink(target))

    def test_handles_missing_source(self):
        source = "nonexistent_source.txt"
        target = "test_dangling_link.txt"
        self.test_files.append(target)

        create_symlink(source, target)

        self.assertTrue(os.path.islink(target))
