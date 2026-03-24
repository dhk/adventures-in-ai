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


if __name__ == "__main__":
    unittest.main()

