"""Candidate-only, no env files, loopback synthetic networking only."""
import os,socket
from pathlib import Path
import app
from app.core.config import Settings
candidate=Path(os.environ['GLOBAL_PARITY_CANDIDATE']).resolve()
assert Path(app.__file__).resolve().is_relative_to(candidate/'apps/backend')
Settings.model_config['env_file']=None
original_connect=socket.socket.connect
original_connect_ex=socket.socket.connect_ex
def checked_connect(sock,address):
 if isinstance(address,tuple):assert address[0] in ('127.0.0.1','localhost','::1'),'external_test_socket_forbidden'
 return original_connect(sock,address)
def checked_connect_ex(sock,address):
 if isinstance(address,tuple):assert address[0] in ('127.0.0.1','localhost','::1'),'external_test_socket_forbidden'
 return original_connect_ex(sock,address)
socket.socket.connect=checked_connect
socket.socket.connect_ex=checked_connect_ex
import app.material_formats as formats
root=Path(__file__).resolve().parents[3]
formats._formats_path=lambda:root/'packages/protocol/src/material-upload-formats.json'
formats.material_upload_formats.cache_clear()
