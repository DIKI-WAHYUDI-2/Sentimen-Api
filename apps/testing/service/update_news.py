from unittest.mock import Mock, patch
from unittest import TestCase

from service.news_service import NewsService

class TestUpdateNews(TestCase):
    @patch('service.news_service.NewsRepository')
    def test_update_news_success_path(self, mock_repo):
        # Arrange
        test_id = 1
        update_data = {'judul': 'Updated Title', 'sentimen': 'negatif'}
        existing_news = Mock()
        existing_news.judul = 'Old Title'
        existing_news.tanggal = '2025-01-01'
        existing_news.sumber = 'Old Source'
        existing_news.link = 'https://old.com'
        existing_news.meta_title = 'Old Meta'
        existing_news.meta_description = 'Old Description'
        existing_news.sentimen = 'positif'

        mock_repo.find_by_id.return_value = existing_news

        # Act
        result = NewsService.update_news(test_id, update_data)

        # Assert
        mock_repo.find_by_id.assert_called_once_with(test_id)
        mock_repo.save.assert_called_once_with(existing_news)
        self.assertEqual(existing_news.judul, 'Updated Title')
        self.assertEqual(existing_news.sentimen, 'negatif')
        self.assertEqual(existing_news.tanggal, '2025-01-01')  # Tidak berubah
        self.assertEqual(result, existing_news)

    @patch('service.news_service.NewsRepository')
    def test_update_news_not_found_path(self, mock_repo):
        # Arrange
        test_id = 999
        update_data = {'judul': 'Updated Title'}
        mock_repo.find_by_id.return_value = None

        # Act
        result = NewsService.update_news(test_id, update_data)

        # Assert
        mock_repo.find_by_id.assert_called_once_with(test_id)
        mock_repo.save.assert_not_called()
        self.assertIsNone(result)