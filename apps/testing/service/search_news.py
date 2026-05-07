from unittest.mock import patch
from unittest import TestCase
from service.news_service import NewsService
from apps.models.news import News

class TestSearchNews(TestCase):
    def setUp(self):
        self.sample_news_object = News(
            title='Test Judul',
            published_at='2025-01-15',
            source='Test Source',
            url='https://test.com',
            content=None,
            sentiment='positif'
        )

    @patch('service.news_service.NewsRepository')
    def test_search_news_calls_repository(self, mock_repo):
        # Arrange
        keyword = "test keyword"
        expected_result = [self.sample_news_object]
        mock_repo.find_by_keyword.return_value = expected_result

        # Act
        result = NewsService.search_news(keyword)

        # Assert
        mock_repo.find_by_keyword.assert_called_once_with(keyword)
        self.assertEqual(result, expected_result)
