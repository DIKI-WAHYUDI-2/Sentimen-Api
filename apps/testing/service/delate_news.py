from unittest.mock import patch
from unittest import TestCase

from service.news_service import NewsService
from apps.models.news import News

class TestDeleteNews(TestCase):

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
    def test_delete_news_success_path(self, mock_repo):
        # Arrange
        test_id = 1
        mock_repo.find_by_id.return_value = self.sample_news_object

        # Act
        result = NewsService.delete_news(test_id)

        # Assert
        mock_repo.find_by_id.assert_called_once_with(test_id)
        mock_repo.delete.assert_called_once_with(test_id)
        self.assertTrue(result)

    @patch('service.news_service.NewsRepository')
    def test_delete_news_not_found_path(self, mock_repo):
        # Arrange
        test_id = 999
        mock_repo.find_by_id.return_value = None

        # Act
        result = NewsService.delete_news(test_id)

        # Assert
        mock_repo.find_by_id.assert_called_once_with(test_id)
        mock_repo.delete.assert_not_called()
        self.assertFalse(result)