import unittest
from xml.sax.saxutils import escape


class TestRssXmlEscape(unittest.TestCase):
    def test_escape(self):
        s = 'A & B < C > D "E"'
        out = escape(s)
        self.assertIn("&amp;", out)
        self.assertIn("&lt;", out)
        self.assertIn("&gt;", out)


if __name__ == "__main__":
    unittest.main()

