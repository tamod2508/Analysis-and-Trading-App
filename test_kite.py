"""
Integration tests for Kite Connect API client
Tests the full pipeline: API → Validation → Database
"""

import pytest
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

from api.kite_client import KiteClient, create_client
from api.auth_handler import AuthHandler, verify_authentication
from database.hdf5_manager import HDF5Manager
from config.settings import config


# Sample data for mocking
SAMPLE_OHLCV_DATA = [
    {
        'date': datetime(2024, 1, 1, 9, 15),
        'open': 2450.50,
        'high': 2455.75,
        'low': 2448.25,
        'close': 2453.00,
        'volume': 125000
    },
    {
        'date': datetime(2024, 1, 1, 9, 30),
        'open': 2453.00,
        'high': 2458.50,
        'low': 2451.00,
        'close': 2456.25,
        'volume': 135000
    },
    {
        'date': datetime(2024, 1, 1, 9, 45),
        'open': 2456.25,
        'high': 2460.00,
        'low': 2454.50,
        'close': 2459.00,
        'volume': 142000
    }
]


@pytest.fixture
def mock_kite_connect():
    """Mock KiteConnect instance"""
    with patch('api.kite_client.KiteConnect') as mock:
        kite_instance = Mock()
        mock.return_value = kite_instance
        
        # Mock methods
        kite_instance.historical_data.return_value = SAMPLE_OHLCV_DATA
        kite_instance.profile.return_value = {
            'user_id': 'TEST123',
            'user_name': 'Test User',
            'email': 'test@example.com'
        }
        kite_instance.instruments.return_value = [
            {
                'instrument_token': 738561,
                'exchange_token': 2884,
                'tradingsymbol': 'RELIANCE',
                'name': 'Reliance Industries Ltd',
                'instrument_type': 'EQ',
                'exchange': 'NSE'
            }
        ]
        
        yield kite_instance


@pytest.fixture
def temp_db(tmp_path):
    """Create temporary test database"""
    db_path = tmp_path / "test_kite.h5"
    manager = HDF5Manager(db_path=str(db_path))
    yield manager
    # Cleanup happens automatically with tmp_path


class TestKiteClient:
    """Test KiteClient functionality"""
    
    def test_client_initialization(self, mock_kite_connect):
        """Test client initializes correctly"""
        client = KiteClient(api_key="test_key", access_token="test_token")
        
        assert client.api_key == "test_key"
        assert client.access_token == "test_token"
        assert client.kite is not None
    
    def test_rate_limiting(self, mock_kite_connect):
        """Test rate limiting enforcement"""
        client = KiteClient(api_key="test_key", access_token="test_token")
        client.kite = mock_kite_connect
        
        import time
        start = time.time()
        
        # Make 3 calls (should take at least 0.66 seconds with 3 req/sec limit)
        for _ in range(3):
            client._make_api_call(mock_kite_connect.profile)
        
        elapsed = time.time() - start
        assert elapsed >= 0.6  # Allow small timing variance
    
    def test_fetch_historical_data(self, mock_kite_connect):
        """Test fetching historical data"""
        client = KiteClient(api_key="test_key", access_token="test_token")
        client.kite = mock_kite_connect
        
        data = client.fetch_historical_data(
            instrument_token=738561,
            from_date=datetime(2024, 1, 1),
            to_date=datetime(2024, 1, 2),
            interval="15minute"
        )
        
        assert len(data) == 3
        assert data[0]['open'] == 2450.50
        assert data[0]['volume'] == 125000
    
    def test_retry_logic(self, mock_kite_connect):
        """Test API retry logic on errors"""
        client = KiteClient(api_key="test_key", access_token="test_token")
        client.kite = mock_kite_connect
        
        # Simulate rate limit error then success
        mock_kite_connect.profile.side_effect = [
            Exception("Too many requests"),
            {'user_id': 'TEST123'}
        ]
        
        # Should retry and succeed
        result = client._make_api_call(mock_kite_connect.profile)
        assert result['user_id'] == 'TEST123'
        assert mock_kite_connect.profile.call_count == 2
    
    def test_fetch_and_save_integration(self, mock_kite_connect, temp_db):
        """Test complete fetch → validate → save workflow"""
        client = KiteClient(api_key="test_key", access_token="test_token")
        client.kite = mock_kite_connect
        client.db = temp_db
        
        result = client.fetch_and_save(
            exchange='NSE',
            symbol='RELIANCE',
            instrument_token=738561,
            from_date=datetime(2024, 1, 1),
            to_date=datetime(2024, 1, 2),
            interval='15minute',
            validate=True,
            overwrite=False
        )
        
        assert result['success'] is True
        assert result['records'] == 3
        assert 'validation' in result
        
        # Verify data was saved
        saved_data = temp_db.get_ohlcv('NSE', 'RELIANCE', '15minute')
        assert saved_data is not None
        assert len(saved_data) == 3
    
    def test_invalid_data_handling(self, mock_kite_connect, temp_db):
        """Test handling of invalid data"""
        # Create invalid data (high < low)
        invalid_data = [
            {
                'date': datetime(2024, 1, 1),
                'open': 100.0,
                'high': 95.0,  # Invalid: high < open
                'low': 90.0,
                'close': 98.0,
                'volume': 1000
            }
        ]
        
        mock_kite_connect.historical_data.return_value = invalid_data
        
        client = KiteClient(api_key="test_key", access_token="test_token")
        client.kite = mock_kite_connect
        client.db = temp_db
        
        result = client.fetch_and_save(
            exchange='NSE',
            symbol='TEST',
            instrument_token=123456,
            from_date=datetime(2024, 1, 1),
            to_date=datetime(2024, 1, 2),
            interval='day',
            validate=True
        )
        
        # Should fail validation
        assert result['success'] is False
        assert 'validation' in result


class TestAuthHandler:
    """Test AuthHandler functionality"""
    
    def test_auth_initialization(self):
        """Test auth handler initialization"""
        handler = AuthHandler(api_key="test_key", api_secret="test_secret")
        
        assert handler.api_key == "test_key"
        assert handler.api_secret == "test_secret"
        assert handler.kite is not None
    
    def test_login_url_generation(self):
        """Test login URL generation"""
        with patch('api.auth_handler.KiteConnect') as mock_kite:
            mock_instance = Mock()
            mock_instance.login_url.return_value = "https://kite.zerodha.com/connect/login?api_key=test"
            mock_kite.return_value = mock_instance
            
            handler = AuthHandler(api_key="test_key", api_secret="test_secret")
            url = handler.get_login_url()
            
            assert "kite.zerodha.com" in url
            assert "api_key" in url
    
    def test_session_generation(self):
        """Test session generation from request token"""
        with patch('api.auth_handler.KiteConnect') as mock_kite:
            mock_instance = Mock()
            mock_instance.generate_session.return_value = {
                'access_token': 'test_access_token_123',
                'user_id': 'TEST123',
                'user_name': 'Test User'
            }
            mock_kite.return_value = mock_instance
            
            handler = AuthHandler(api_key="test_key", api_secret="test_secret")
            session = handler.generate_session("test_request_token")
            
            assert session['access_token'] == 'test_access_token_123'
            assert handler.access_token == 'test_access_token_123'
    
    def test_token_verification(self):
        """Test access token verification"""
        with patch('api.auth_handler.KiteConnect') as mock_kite:
            mock_instance = Mock()
            mock_instance.profile.return_value = {
                'user_id': 'TEST123',
                'user_name': 'Test User',
                'email': 'test@example.com'
            }
            mock_kite.return_value = mock_instance
            
            handler = AuthHandler(api_key="test_key", api_secret="test_secret")
            handler.access_token = "test_token"
            
            is_valid = handler.verify_token()
            assert is_valid is True


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows"""
    
    def test_full_data_pipeline(self, mock_kite_connect, temp_db):
        """Test: authenticate → fetch → validate → save → retrieve"""
        
        # 1. Setup authenticated client
        client = KiteClient(api_key="test_key", access_token="test_token")
        client.kite = mock_kite_connect
        client.db = temp_db
        
        # 2. Fetch and save data
        result = client.fetch_and_save(
            exchange='NSE',
            symbol='RELIANCE',
            instrument_token=738561,
            from_date=datetime(2024, 1, 1),
            to_date=datetime(2024, 1, 2),
            interval='15minute'
        )
        
        assert result['success'] is True
        
        # 3. Retrieve and verify data
        df = temp_db.get_ohlcv('NSE', 'RELIANCE', '15minute')
        assert df is not None
        assert len(df) == 3
        assert df['close'].iloc[0] == 2453.00
        
        # 4. Check database stats
        stats = temp_db.get_database_stats()
        assert stats['total_symbols'] == 1
        assert stats['total_rows'] == 3
    
    def test_multiple_intervals(self, mock_kite_connect, temp_db):
        """Test fetching multiple intervals for same symbol"""
        client = KiteClient(api_key="test_key", access_token="test_token")
        client.kite = mock_kite_connect
        client.db = temp_db
        
        intervals = ['15minute', '60minute', 'day']
        
        for interval in intervals:
            result = client.fetch_and_save(
                exchange='NSE',
                symbol='RELIANCE',
                instrument_token=738561,
                from_date=datetime(2024, 1, 1),
                to_date=datetime(2024, 1, 2),
                interval=interval
            )
            assert result['success'] is True
        
        # Verify all intervals saved
        summary = temp_db.get_symbol_summary('NSE', 'RELIANCE')
        assert len(summary['intervals']) == 3
        assert '15minute' in summary['intervals']
        assert '60minute' in summary['intervals']
        assert 'day' in summary['intervals']
    
    def test_incremental_update(self, mock_kite_connect, temp_db):
        """Test incremental data updates"""
        client = KiteClient(api_key="test_key", access_token="test_token")
        client.kite = mock_kite_connect
        client.db = temp_db
        
        # Initial fetch
        result1 = client.fetch_and_save(
            exchange='NSE',
            symbol='RELIANCE',
            instrument_token=738561,
            from_date=datetime(2024, 1, 1),
            to_date=datetime(2024, 1, 2),
            interval='day'
        )
        assert result1['success'] is True
        
        # Add more data (should append)
        new_data = [
            {
                'date': datetime(2024, 1, 3),
                'open': 2460.00,
                'high': 2465.00,
                'low': 2458.00,
                'close': 2463.00,
                'volume': 150000
            }
        ]
        mock_kite_connect.historical_data.return_value = new_data
        
        result2 = client.fetch_and_save(
            exchange='NSE',
            symbol='RELIANCE',
            instrument_token=738561,
            from_date=datetime(2024, 1, 3),
            to_date=datetime(2024, 1, 3),
            interval='day',
            overwrite=False
        )
        assert result2['success'] is True
        
        # Verify combined data
        df = temp_db.get_ohlcv('NSE', 'RELIANCE', 'day')
        assert len(df) == 4  # 3 original + 1 new


# Performance tests
class TestPerformance:
    """Test performance characteristics"""
    
    def test_batch_processing(self, mock_kite_connect, temp_db):
        """Test batch processing of multiple symbols"""
        client = KiteClient(api_key="test_key", access_token="test_token")
        client.kite = mock_kite_connect
        client.db = temp_db
        
        instruments = [
            {'exchange': 'NSE', 'symbol': 'RELIANCE', 'instrument_token': 738561},
            {'exchange': 'NSE', 'symbol': 'TCS', 'instrument_token': 2953217},
            {'exchange': 'NSE', 'symbol': 'INFY', 'instrument_token': 408065},
        ]
        
        summary = client.fetch_multiple_symbols(
            instruments=instruments,
            from_date=datetime(2024, 1, 1),
            to_date=datetime(2024, 1, 2),
            intervals=['day'],
            validate=True
        )
        
        assert summary['total_tasks'] == 3
        assert summary['successful'] == 3
        assert summary['success_rate'] == 100.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])