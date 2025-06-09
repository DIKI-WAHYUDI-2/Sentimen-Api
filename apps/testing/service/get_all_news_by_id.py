from unittest.mock import patch
from unittest import TestCase

from service.news_service import NewsService
from apps.models.news import News

class TestGetAllNewsById(TestCase):
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
    def test_get_news_by_id_calls_repository(self, mock_repo):
        # Arrange
        test_id = 1
        mock_repo.find_by_id.return_value = self.sample_news_object

        # Act
        result = NewsService.get_news(test_id)

        # Assert
        mock_repo.find_by_id.assert_called_once_with(test_id)
        self.assertEqual(result, self.sample_news_object)