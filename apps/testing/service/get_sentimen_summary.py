from unittest.mock import patch
from unittest import TestCase
from service.news_service import NewsService

class TestGetSentimenSummary(TestCase):

    @patch('service.news_service.NewsRepository')
    def test_get_sentimen_summary_calls_repository(self, mock_repo):
        """Test bahwa get_sentimen_summary memanggil NewsRepository.get_sentimen_data"""
        # Arrange
        expected_result = {'positif': 10, 'negatif': 5, 'netral': 3}
        mock_repo.get_sentimen_data.return_value = expected_result

        # Act
        result = NewsService.get_sentimen_summary()

        # Assert
        mock_repo.get_sentimen_data.assert_called_once()
        self.assertEqual(result, expected_result)