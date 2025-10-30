import os
import django
import pytest

# Configure Django settings for testing
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

@pytest.fixture(scope='session')
def django_db_setup():
    """Configure Django database for testing"""
    pass 