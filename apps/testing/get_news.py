from datetime import datetime, timedelta
from unittest import TestCase
from unittest.mock import patch, MagicMock
import requests
from utils.scraper import get_news
import utils.scraper


class TestGetNews(TestCase):
    def setUp(self):
        # Sample news data template
        self.sample_news = {
            "title": "Test News",
            "date": "raw_date",
            "source": "Test Source",
            "link": "http://valid.url"
        }

        # Sample content data template
        self.sample_content = {
            "meta_title": "Mock Title",
            "meta_description": "Mock Description",
            "content": "Mock Content"
        }

    @patch('utils.scraper.requests.get')
    @patch('utils.scraper.convert_date')
    @patch('utils.scraper.is_today')
    @patch('utils.scraper.get_news_content')
    def test_success_flow(self, mock_content, mock_today, mock_convert, mock_get):
        utils.scraper.QUERIES = ["PTPN IV Regional III"]
        # Setup mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "news_results": [self.sample_news]
        }
        mock_get.return_value = mock_response

        # Setup mock dependencies
        mock_convert.return_value = datetime.now().strftime("%Y-%m-%d")
        mock_today.return_value = True
        mock_content.return_value = self.sample_content

        # Execute and verify
        results = get_news()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], self.sample_news["title"])
        self.assertEqual(results[0]["source"], self.sample_news["source"])
        mock_get.assert_called()
        mock_content.assert_called_once_with(self.sample_news["link"])

    @patch('data.berita.requests.get')
    def test_api_failure(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("Timeout")

        results = get_news()
        self.assertEqual(results, [])
        mock_get.assert_called()

    @patch('utils.scraper.requests.get')
    @patch('utils.scraper.convert_date')
    @patch('utils.scraper.is_today')
    @patch('utils.scraper.get_news_content')
    def test_date_filtering(self, mock_content, mock_today, mock_convert, mock_get):
        utils.scraper.QUERIES = ["PTPN IV Regional III"]
        # Setup mock with multiple news items
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "news_results": [
                {**self.sample_news, "link": "http://url1"},
                {**self.sample_news, "link": "http://url2"}
            ]
        }
        mock_get.return_value = mock_response

        mock_content.return_value = self.sample_content  # <<=== ini yang kamu lupa

        # Test 1: All news are today
        today = datetime.now().strftime("%Y-%m-%d")
        mock_convert.return_value = today
        mock_today.return_value = True

        results = get_news()
        self.assertEqual(len(results), 2)

        # Test 2: All news are old
        mock_convert.side_effect = ["2023-01-01", "2023-01-01"]
        mock_today.return_value = False

        results = get_news()
        self.assertEqual(len(results), 0)

        # Test 3: Mixed dates
        mock_convert.side_effect = [today, "2023-01-01"]
        mock_today.side_effect = [True, False]

        results = get_news()
        self.assertEqual(len(results), 1)
