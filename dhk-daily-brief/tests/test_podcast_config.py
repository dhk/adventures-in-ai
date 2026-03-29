import unittest

from dhk_daily_brief_imports import podcast_config


class TestPodcastConfig(unittest.TestCase):
    def test_parse_episode_title_from_filename_known_slug(self):
        title = podcast_config.parse_episode_title_from_filename("2026-03-21-news.m4a")
        self.assertEqual(title, "reading list - news - 2026-03-21")

    def test_parse_episode_title_from_filename_professional(self):
        title = podcast_config.parse_episode_title_from_filename("2026-03-01-professional.mp3")
        self.assertEqual(title, "reading list - professional - 2026-03-01")

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

    def test_elementfm_episode_description_fallback(self):
        d = podcast_config.elementfm_episode_description("reading list - think - 2026-03-24")
        self.assertIn("DHK Daily Brief", d)
        self.assertIn("think", d)

    def test_elementfm_episode_description_rich(self):
        rich = "How Power Profits From Chaos\n\n• Idea one\n• Idea two\n\nSources: Noahpinion"
        d = podcast_config.elementfm_episode_description("reading list - think - 2026-03-24", rich)
        self.assertEqual(d, rich)

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
        # Skill sometimes generates variant titles — emoji is the reliable signal
        self.assertEqual(
            podcast_config.category_title_to_slug("📰 Today's News"),
            "news",
        )
        self.assertEqual(
            podcast_config.category_title_to_slug("📰 Weekend Reading"),
            "news",
        )
        self.assertEqual(
            podcast_config.category_title_to_slug("🧠 Ideas Worth Considering"),
            "think",
        )
        self.assertEqual(
            podcast_config.category_title_to_slug("💼 Tech & Career"),
            "professional",
        )


if __name__ == "__main__":
    unittest.main()

