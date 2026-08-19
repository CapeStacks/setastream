import unittest

from certificate_engine.config import FieldConfig, TemplateConfig
from certificate_engine.exceptions import ConfigurationError

from .helpers import configuration_mapping


class TemplateConfigurationTests(unittest.TestCase):
    def test_parses_readable_configuration_objects(self):
        config = TemplateConfig.from_mapping(configuration_mapping())

        self.assertEqual(config.template_name, "Test Certificate")
        self.assertIsInstance(config.fields[0], FieldConfig)
        self.assertEqual(
            config.required_data_keys,
            ("recipient_name", "certificate_number"),
        )

    def test_rejects_coordinate_outside_normalized_range(self):
        value = configuration_mapping()
        value["fields"][0]["x"] = 1.1

        with self.assertRaisesRegex(ConfigurationError, "from 0 to 1"):
            TemplateConfig.from_mapping(value)

    def test_rejects_unknown_font(self):
        value = configuration_mapping()
        value["fields"][0]["font_name"] = "ClientUploadedFont"

        with self.assertRaisesRegex(ConfigurationError, "built-in font"):
            TemplateConfig.from_mapping(value)

    def test_rejects_minimum_font_above_starting_size(self):
        value = configuration_mapping()
        value["fields"][0]["minimum_font_size"] = 33

        with self.assertRaisesRegex(ConfigurationError, "cannot exceed"):
            TemplateConfig.from_mapping(value)
