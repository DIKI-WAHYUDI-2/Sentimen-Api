from unittest.mock import Mock, patch
from unittest import TestCase
from service.news_service import NewsService

class TestCreateNews(TestCase):
    def setUp(self):
        self.sample_news_data = {
            'judul': 'Test Judul',
            'tanggal': '2025-01-15',
            'sumber': 'Test Source',
            'link': 'https://test.com',
            'meta_title': 'Test Meta Title',
            'meta_description': 'Test Meta Description',
            'sentimen': 'positif'
        }

    @patch('service.news_service.NewsRepository')
    @patch('service.news_service.News')
    def test_create_news_creates_news_object_and_saves(self, mock_news_class, mock_repo):
        # Arrange
        mock_news_instance = Mock()
        mock_news_class.return_value = mock_news_instance
        mock_repo.save.return_value = mock_news_instance

        # Act
        result = NewsService.create_news(self.sample_news_data)

        # Assert
        mock_news_class.assert_called_once_with(
            judul=self.sample_news_data['judul'],
            tanggal=self.sample_news_data['tanggal'],
            sumber=self.sample_news_data['sumber'],
            link=self.sample_news_data['link'],
            meta_title=self.sample_news_data['meta_title'],
            meta_description=self.sample_news_data['meta_description'],
            sentimen=self.sample_news_data['sentimen']
        )
        mock_repo.save.assert_called_once_with(mock_news_instance)
        self.assertEqual(result, mock_news_instance)


