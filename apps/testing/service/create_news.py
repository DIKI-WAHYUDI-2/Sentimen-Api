from unittest.mock import ANY, Mock, patch
from unittest import TestCase
from service.news_service import NewsService

class TestCreateNews(TestCase):
    def setUp(self):
        self.sample_news_data = {
            'judul': 'Test Judul',
            'tanggal': '2025-01-15',
            'sumber': 'Test Source',
            'link': 'https://test.com',
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
            title=self.sample_news_data['judul'],
            published_at=ANY,
            source=self.sample_news_data['sumber'],
            url=self.sample_news_data['link'],
            content=None,
            sentiment=self.sample_news_data['sentimen']
        )
        mock_repo.save.assert_called_once_with(mock_news_instance)
        self.assertEqual(result, mock_news_instance)


