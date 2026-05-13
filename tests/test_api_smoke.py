import unittest

from app import app


class ApiSmokeTest(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_api_items_returns_list(self):
        response = self.client.get("/api/items?lang=en")
        self.assertEqual(response.status_code, 200)
        self.assertIn("noindex", response.headers.get("X-Robots-Tag", ""))

        payload = response.get_json()
        self.assertIsInstance(payload, dict)

        list_key = next((k for k, v in payload.items() if isinstance(v, list)), None)
        self.assertIsNotNone(list_key)
        self.assertIn("last_updated", payload)

    def test_robots_and_sitemap_exist(self):
        robots = self.client.get("/robots.txt")
        self.assertEqual(robots.status_code, 200)
        self.assertIn("Sitemap:", robots.get_data(as_text=True))

        sitemap = self.client.get("/sitemap.xml")
        self.assertEqual(sitemap.status_code, 200)
        body = sitemap.get_data(as_text=True)
        self.assertIn("<urlset", body)
        self.assertIn("<loc>", body)
        self.assertIn("xhtml:link", body)

    def test_favicon_and_manifest_routes_exist(self):
        favicon = self.client.get("/favicon.ico")
        self.assertIn(favicon.status_code, (200, 302))

        manifest = self.client.get("/site.webmanifest")
        self.assertEqual(manifest.status_code, 200)
        self.assertIn("icons", manifest.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
