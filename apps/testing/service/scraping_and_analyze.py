from unittest.mock import patch
from unittest import TestCase

from service.news_service import NewsService

class TestScrapingAndAnalyze(TestCase):
    @patch('service.news_service.NewsRepository')
    @patch('service.news_service.analyze_sentiment')
    @patch('service.news_service.get_news')
    def test_scraping_and_analyze_success_path(self, mock_get_news, mock_analyze_sentiment, mock_repo):
        # Arrange
        test_data = "test_query"
        mock_news_data = [
            {
                'title': 'Test News 1',
                'date': '2025-01-15',
                'source': {'name': 'Test Source'},
                'link': 'https://test1.com',
                'meta_title': 'Meta Title 1',
                'meta_description': 'Meta Description 1'
            },
            {
                'title': 'Test News 2',
                'date': '2025-01-16',
                'source': 'String Source',
                'link': 'https://test2.com',
                'meta_title': 'Meta Title 2',
                'meta_description': 'Meta Description 2'
            }
        ]

        mock_get_news.return_value = mock_news_data
        mock_analyze_sentiment.side_effect = ['positif', 'negatif']

        # Act
        result = NewsService.scraping_and_analyze(test_data)

        # Assert
        mock_get_news.assert_called_once_with(test_data)
        self.assertEqual(mock_analyze_sentiment.call_count, 2)
        self.assertEqual(mock_repo.save.call_count, 2)
        self.assertEqual(result, mock_news_data)

    @patch('service.news_service.NewsRepository')
    @patch('service.news_service.analyze_sentiment')
    @patch('service.news_service.get_news')
    def test_scraping_and_analyze_no_data_path(self, mock_get_news, mock_analyze_sentiment, mock_repo):
        # Arrange
        test_data = "test_query"
        mock_get_news.return_value = None

        # Act
        result = NewsService.scraping_and_analyze(test_data)

        # Assert
        mock_get_news.assert_called_once_with(test_data)
        mock_analyze_sentiment.assert_not_called()
        mock_repo.save.assert_not_called()
        self.assertIsNone(result)

    @patch('service.news_service.NewsRepository')
    @patch('service.news_service.analyze_sentiment')
    @patch('service.news_service.get_news')
    @patch('builtins.print')
    def test_scraping_and_analyze_exception_handling(self, mock_print, mock_get_news, mock_analyze_sentiment,
                                                     mock_repo):
        # Arrange
        test_data = "test_query"
        mock_news_data = [
            {
                'title': 'Test News',
                'date': '2025-01-15',
                'source': {'name': 'Test Source'},
                'link': 'https://test.com'
            }
        ]

        mock_get_news.return_value = mock_news_data
        mock_analyze_sentiment.side_effect = Exception("Sentiment analysis failed")

        # Act
        result = NewsService.scraping_and_analyze(test_data)

        # Assert
        mock_print.assert_called_once()
        self.assertIn("Error saat memproses berita", str(mock_print.call_args))
        self.assertEqual(result, mock_news_data)