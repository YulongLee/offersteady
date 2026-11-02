"""All values synthetic; never allow real provider or database sockets."""
import os,socket
import pytest
os.environ.update({'OFFERSTEADY_ENVIRONMENT':'test','OFFERSTEADY_PRODUCT_EDITION':'global','OFFERSTEADY_DATABASE_URL':'','OFFERSTEADY_REDIS_URL':'','OFFERSTEADY_AUTH_SMS_PROVIDER_MODE':'fake','OFFERSTEADY_AUTH_EMAIL_PROVIDER_MODE':'fake'})
@pytest.fixture(autouse=True)
def no_network(monkeypatch):
 def blocked(*args,**kwargs):raise AssertionError('unexpected real network access')
 monkeypatch.setattr(socket.socket,'connect',blocked)
 monkeypatch.setattr(socket,'create_connection',blocked)
