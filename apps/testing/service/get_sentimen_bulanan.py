from unittest.mock import patch
from unittest import TestCase
from datetime import date

from service.news_service import NewsService

class TestGetSentimenBulanan(TestCase):
    @patch('service.news_service.NewsRepository')
    def test_get_sentimen_bulanan_processing_logic(self, mock_repo):
        # Arrange
        mock_data = [
            (date(2025, 1, 15), 'positif'),
            (date(2025, 1, 20), 'negatif'),
            (date(2025, 2, 10), 'positif'),
            (date(2025, 2, 15), 'positif'),
            (date(2025, 3, 5), 'netral'),
        ]
        mock_repo.get_sentimen_and_date.return_value = mock_data

        # Act
        result = NewsService.get_sentimen_bulanan()

        # Assert
        mock_repo.get_sentimen_and_date.assert_called_once()

        # Verifikasi hasil processing
        self.assertIsInstance(result, list)

        # Cari data untuk bulan Januari (bulan 1)
        januari_data = next((item for item in result if item['bulan'] == 'Januari'), None)
        self.assertIsNotNone(januari_data)
        self.assertEqual(januari_data['positif'], 1)
        self.assertEqual(januari_data['negatif'], 1)
        self.assertEqual(januari_data['netral'], 0)

        # Cari data untuk bulan Februari (bulan 2)
        februari_data = next((item for item in result if item['bulan'] == 'Februari'), None)
        self.assertIsNotNone(februari_data)
        self.assertEqual(februari_data['positif'], 2)
        self.assertEqual(februari_data['negatif'], 0)
        self.assertEqual(februari_data['netral'], 0)


    @patch('service.news_service.NewsRepository')
    def test_get_sentimen_bulanan_with_whitespace_sentimen(self, mock_repo):
        # Arrange
        mock_data = [
            (date(2025, 1, 15), ' positif '),  # dengan whitespace
            (date(2025, 1, 20), 'NEGATIF'),  # uppercase
        ]
        mock_repo.get_sentimen_and_date.return_value = mock_data

        # Act
        result = NewsService.get_sentimen_bulanan()

        # Assert
        januari_data = next((item for item in result if item['bulan'] == 'Januari'), None)
        self.assertIsNotNone(januari_data)
        self.assertEqual(januari_data['positif'], 1)  # whitespace di-strip dan di-lowercase
        self.assertEqual(januari_data['negatif'], 1)  # uppercase di-lowercase


    @patch('service.news_service.NewsRepository')
    def test_get_sentimen_bulanan_empty_data(self, mock_repo):
        # Arrange
        mock_repo.get_sentimen_and_date.return_value = []

        # Act
        result = NewsService.get_sentimen_bulanan()

        # Assert
        mock_repo.get_sentimen_and_date.assert_called_once()
        self.assertEqual(result, [])


    def test_get_sentimen_bulanan_month_mapping(self):
        bulan_map = {
            1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
            5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
            9: "September", 10: "Oktober", 11: "November", 12: "Desember"
        }

        # Verifikasi semua bulan ada
        self.assertEqual(len(bulan_map), 12)
        self.assertEqual(bulan_map[1], "Januari")
        self.assertEqual(bulan_map[12], "Desember")
