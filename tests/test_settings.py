import os
import unittest
from unittest.mock import patch

from bbi_os.settings import get_settings, load_settings, reset_settings_cache


BBIOS_ENV_KEYS = (
    "BBIOS_APP_NAME",
    "BBIOS_APP_VERSION",
    "BBIOS_ENVIRONMENT",
    "BBIOS_DEBUG",
    "BBIOS_HOST",
    "BBIOS_PORT",
    "BBIOS_LOG_LEVEL",
    "BBIOS_API_PREFIX",
    "BBIOS_DATA_DIR",
)


class SettingsTests(unittest.TestCase):
    def tearDown(self) -> None:
        reset_settings_cache()

    def test_defaults_are_safe_for_local_development(self) -> None:
        settings = load_settings({})

        self.assertEqual(settings.app_name, "BBIOS OS")
        self.assertEqual(settings.app_version, "1.0")
        self.assertEqual(settings.environment, "local")
        self.assertFalse(settings.debug)
        self.assertEqual(settings.host, "127.0.0.1")
        self.assertEqual(settings.port, 8000)
        self.assertEqual(settings.log_level, "INFO")
        self.assertEqual(settings.api_prefix, "/cockpit")
        self.assertEqual(str(settings.data_dir), "data")

    def test_environment_overrides_are_applied(self) -> None:
        settings = load_settings(
            {
                "BBIOS_APP_NAME": "Custom BBIOS",
                "BBIOS_APP_VERSION": "2.0",
                "BBIOS_ENVIRONMENT": "staging",
                "BBIOS_DEBUG": "true",
                "BBIOS_HOST": "0.0.0.0",
                "BBIOS_PORT": "9000",
                "BBIOS_LOG_LEVEL": "debug",
                "BBIOS_API_PREFIX": "/custom",
                "BBIOS_DATA_DIR": "/tmp/bbios-data",
            }
        )

        self.assertEqual(settings.app_name, "Custom BBIOS")
        self.assertEqual(settings.app_version, "2.0")
        self.assertEqual(settings.environment, "staging")
        self.assertTrue(settings.debug)
        self.assertEqual(settings.host, "0.0.0.0")
        self.assertEqual(settings.port, 9000)
        self.assertEqual(settings.log_level, "DEBUG")
        self.assertEqual(settings.api_prefix, "/custom")
        self.assertEqual(str(settings.data_dir), "/tmp/bbios-data")

    def test_boolean_parsing_accepts_common_values(self) -> None:
        for value in ("1", "true", "yes", "on"):
            self.assertTrue(load_settings({"BBIOS_DEBUG": value}).debug)
        for value in ("0", "false", "no", "off"):
            self.assertFalse(load_settings({"BBIOS_DEBUG": value}).debug)

    def test_invalid_boolean_raises_value_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "BBIOS_DEBUG"):
            load_settings({"BBIOS_DEBUG": "sometimes"})

    def test_invalid_integer_raises_value_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "BBIOS_PORT"):
            load_settings({"BBIOS_PORT": "eight-thousand"})

    def test_invalid_port_range_raises_value_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "BBIOS_PORT"):
            load_settings({"BBIOS_PORT": "70000"})

    def test_settings_cache_can_be_reset_between_environment_changes(self) -> None:
        with patch.dict(os.environ, {"BBIOS_APP_NAME": "First"}, clear=False):
            for key in BBIOS_ENV_KEYS:
                if key != "BBIOS_APP_NAME":
                    os.environ.pop(key, None)
            reset_settings_cache()
            self.assertEqual(get_settings().app_name, "First")

        with patch.dict(os.environ, {"BBIOS_APP_NAME": "Second"}, clear=False):
            for key in BBIOS_ENV_KEYS:
                if key != "BBIOS_APP_NAME":
                    os.environ.pop(key, None)
            reset_settings_cache()
            self.assertEqual(get_settings().app_name, "Second")

    def test_no_secret_environment_variable_is_required(self) -> None:
        settings = load_settings({})

        self.assertEqual(settings.environment, "local")
        self.assertFalse(
            any("SECRET" in key or "TOKEN" in key or "PASSWORD" in key for key in BBIOS_ENV_KEYS)
        )


if __name__ == "__main__":
    unittest.main()
