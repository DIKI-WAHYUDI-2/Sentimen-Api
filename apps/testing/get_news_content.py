from unittest import TestCase
from unittest.mock import patch, MagicMock
import requests
from utils.scraper import get_news_content

class TestNewsContent(TestCase):
    #Pengujian Fungsi get_news
    @patch('requests.get')
    def test_success_with_complete_elements(self, mock_get):
        # Mock response dengan HTML lengkap
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <head>
                <title>Test Title</title>
                <meta name="description" content="Test Description">
            </head>
        </html>
        """
        mock_get.return_value = mock_response

        result = get_news_content("https://www.lintas10.com/ibu-karyawan-palm-co-ptpn-iv-regional-iii-buat-laporan-ke-polsek-lubuk-dalam-ini-kronologinya.html")
        self.assertEqual(result, {
            "meta_title": "Test Title",
            "meta_description": "Test Description"
        })

    @patch('requests.get')
    def test_success_with_missing_elements(self, mock_get):
        # Mock response tanpa meta description
        mock_response = MagicMock()
        mock_response.text = """"
        <html>
            <head>
                <title>Only Title</title>
            </head>
        </html>
        """
        mock_get.return_value = mock_response

        result = get_news_content("https://www.lintas10.com/ibu-karyawan-palm-co-ptpn-iv-regional-iii-buat-laporan-ke-polsek-lubuk-dalam-ini-kronologinya.html")
        self.assertEqual(result, {
            "meta_title": "Only Title",
            "meta_description": "Deskripsi tidak ditemukan"
        })

    @patch('requests.get')
    def test_request_timeout(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout()
        html = """
        <!DOCTYPE html>
            <html>
            <head>
                <title>Timeout Redirect</title>
                <script>
                    // Redirect setelah 5 detik (5000 milidetik)
                    setTimeout(function() {
                        window.location.href = "https://example.com";
                    }, 5000);
                </script>
            </head>
            <body>
                <h1>Halaman ini akan redirect dalam 5 detik...</h1>
            </body>
            </html>"""
        result = get_news_content(html)
        self.assertEqual(result, {
            "meta_title": "Error",
            "meta_description": "Error"
        })