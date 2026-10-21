import unittest
from unittest.mock import patch

from ysx_studio import translator
from ysx_studio.web_api import translation_config_from_ui


class DeepLEndpointTests(unittest.TestCase):
    def test_ui_ignores_custom_endpoint_for_deepl(self):
        config = translation_config_from_ui({
            "provider": "deepl-free",
            "api_key": "example:fx",
            "endpoint": "https://example.invalid",
        })
        self.assertFalse(hasattr(config, "endpoint"))
        self.assertEqual(translator.deepl_endpoint(config), "https://api-free.deepl.com")

    def test_free_and_pro_use_distinct_official_hosts(self):
        free = translator.TranslationConfig("deepl-free", "key")
        pro = translator.TranslationConfig("deepl-pro", "key:fx")
        self.assertEqual(translator.deepl_endpoint(free), "https://api-free.deepl.com")
        self.assertEqual(translator.deepl_endpoint(pro), "https://api.deepl.com")

    @patch("ysx_studio.translator._request")
    def test_unsupported_provider_never_sends_request(self, request):
        from ysx_studio import core
        with self.assertRaises(core.StudioError):
            translator.translate_batch(translator.TranslationConfig("removed-provider", "example"), ["Hello"])
        request.assert_not_called()
        with self.assertRaises(core.StudioError):
            translation_config_from_ui({"provider": "removed-provider", "api_key": "example"})

    def test_default_provider_is_deepl_free(self):
        self.assertEqual(translation_config_from_ui({"api_key": "example:fx"}).provider, "deepl-free")

    @patch("ysx_studio.translator._request")
    def test_free_translation_calls_v2_translate(self, request):
        request.return_value = {"translations": [{"text": "<r>Olá</r>"}]}
        config = translator.TranslationConfig("deepl-free", "example:fx")
        self.assertEqual(translator.translate_batch(config, ["Hello"]), ["Olá"])
        self.assertEqual(request.call_args.args[0], "https://api-free.deepl.com/v2/translate")

    @patch("ysx_studio.translator._request")
    def test_deepl_context_and_continuous_source_are_sent(self, request):
        request.return_value = {"translations": [{"text": "<r>Uma aventura <x>__YSX0000__</x></r>"}]}
        config = translator.TranslationConfig("deepl-free", "example:fx")
        result = translator.translate_batch(config, ["An adven-\nture\n<C1>"])
        body = request.call_args.args[1]
        self.assertEqual(result, ["Uma aventura <C1>"])
        self.assertEqual(body["split_sentences"], "1")
        self.assertFalse(body["preserve_formatting"])
        self.assertEqual(body["context"], translator.DEEPL_FANTASY_CONTEXT)
        self.assertIn("An adventure", body["text"][0])
        self.assertNotIn("\n", body["text"][0])

    def test_normalize_deepl_source_joins_visual_lines(self):
        self.assertEqual(
            translator.normalize_deepl_source("A long&#x20;\nline and adven-\nture."),
            "A long line and adventure.",
        )


if __name__ == "__main__":
    unittest.main()
