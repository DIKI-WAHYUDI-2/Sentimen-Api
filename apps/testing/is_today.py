from datetime import datetime
from unittest import TestCase
from unittest.mock import patch
from utils.scraper import is_today

class TestIsToday   (TestCase):
    # Pengujian Fungsi is_today
    def test_is_today_true(sefl):
        # Mock datetime.utcnow() untuk selalu mengembalikan tanggal tertentu
        with patch("utils.scraper.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2023, 10, 5)
            assert is_today("2023-10-05","2023-10-05") is True


    def test_is_today_false(sefl):
        with patch("utils.scraper.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2023, 10, 5)
            assert is_today("2023-10-05","2023-10-04") is False