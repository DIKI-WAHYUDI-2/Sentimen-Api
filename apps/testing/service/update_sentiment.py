from unittest.mock import Mock, patch
from unittest import TestCase

from service.news_service import NewsService

class TestUpdateSentiment(TestCase):
    @patch('service.news_service.NewsRepository')
    def test_update_sentiment_success_path(self, mock_repo):
        # Arrange
        test_id = 1
        new_sentiment = 'negatif'
        existing_news = Mock()
        existing_news.sentimen = 'positif'
        mock_repo.find_by_id.return_value = existing_news

        # Act
        result = NewsService.update_sentiment(test_id, new_sentiment)

        # Assert
        mock_repo.find_by_id.assert_called_once_with(test_id)
        mock_repo.save.assert_called_once_with(existing_news)
        self.assertEqual(existing_news.sentimen, new_sentiment)
        self.assertEqual(result, existing_news)

    @patch('service.news_service.NewsRepository')
    def test_update_sentiment_not_found_path(self, mock_repo):
        # Arrange
        test_id = 999
        new_sentiment = 'negatif'
        mock_repo.find_by_id.return_value = None

        # Act
        result = NewsService.update_sentiment(test_id, new_sentiment)

        # Assert
        mock_repo.find_by_id.assert_called_once_with(test_id)
        mock_repo.save.assert_not_called()
        self.assertIsNone(result)
