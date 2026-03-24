import unittest

from dhk_daily_brief_imports import podcast_config


class TestPodcastConfig(unittest.TestCase):
    def test_parse_episode_title_from_filename_known_slug(self):
        title = podcast_config.parse_episode_title_from_filename("2026-03-21-news.m4a")
        self.assertIn("📰 News & Current Affairs", title)
        self.assertIn("Mar", title)
        self.assertIn("2026", title)

    def test_parse_episode_title_from_filename_fallback(self):
        title = podcast_config.parse_episode_title_from_filename("weird_name-file.m4a")
        self.assertEqual(title, "Weird Name File")

    def test_parse_reading_list_notebook_title(self):
        parsed = podcast_config.parse_reading_list_notebook_title(
            "reading-list-2026-03-21-03 🧠 Things to Think About"
        )
        self.assertEqual(parsed, ("2026-03-21", 3, "🧠 Things to Think About"))

    def test_parse_audio_filename(self):
        parsed = podcast_config.parse_audio_filename("2026-03-21-news.mp3")
        self.assertEqual(parsed, ("2026-03-21", "news", "mp3"))

    def test_slug_for_category_title(self):
        slug = podcast_config.slug_for_category_title("📰 News & Current Affairs")
        self.assertEqual(slug, "news")

    def test_elementfm_episode_description_nonempty(self):
        d = podcast_config.elementfm_episode_description("🧠 Things — Mar 24, 2026")
        self.assertTrue(len(d) > 10)

    def test_category_title_to_slug_variants(self):
        self.assertEqual(
            podcast_config.category_title_to_slug("📰 News & Current Affairs"),
            "news",
        )
        self.assertEqual(
            podcast_config.category_title_to_slug("News and Current Affairs"),
            "news",
        )
        self.assertEqual(
            podcast_config.category_title_to_slug("🧠 Things to Think About"),
            "think",
        )


if __name__ == "__main__":
    unittest.main()

