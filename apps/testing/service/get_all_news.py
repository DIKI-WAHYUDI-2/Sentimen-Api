from unittest.mock import patch
from unittest import TestCase

from service.news_service import NewsService
from apps.models.news import News


class TestGetAllNews(TestCase):
    def setUp(self):
        self.sample_news_object = News(
            judul='Test Judul',
            tanggal='2025-01-15',
            sumber='Test Source',
            link='https://test.com',
            meta_title='Test Meta Title',
            meta_description='Test Meta Description',
            sentimen='positif'
        )

    @patch('service.news_service.NewsRepository')
    def test_get_all_news_calls_repository(self, mock_repo):
        # Arrange
        expected_news = [self.sample_news_object]
        mock_repo.find_all.return_value = expected_news

        # Act
        result = NewsService.get_all_news()

        # Assert
        mock_repo.find_all.assert_called_once()
        self.assertEqual(result, expected_news)

