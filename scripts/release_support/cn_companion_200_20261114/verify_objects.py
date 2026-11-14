"""Read-only, streaming verification of this frozen CN release and previous objects."""
import hashlib
import json
import logging

EXPECTED = [{'key': 'desktop-releases/macos/arm64/2.0.0/OfferSteady-Companion-2.0.0-macOS-arm64.dmg', 'size': 136608975, 'sha256': '99eeea79ef001e37c1347e8c87493291177973db83ded048f33421966904bbad', 'contentType': 'application/x-apple-diskimage'}, {'key': 'desktop-releases/macos/x64/2.0.0/OfferSteady-Companion-2.0.0-macOS-x64.dmg', 'size': 142139062, 'sha256': '8cdfbf524ce8abf0763a7e28c8d647781405deb5f0574412624f4f857527b27f', 'contentType': 'application/x-apple-diskimage'}, {'key': 'desktop-releases/windows/x64/2.0.0/OfferSteady-Companion-Setup-2.0.0-Windows-x64.exe', 'size': 102182232, 'sha256': '2ca70baa786662c176d2a3d78831e5c1029a1369dfd68e15d799dbb5346a8af8', 'contentType': 'application/vnd.microsoft.portable-executable'}, {'key': 'desktop-releases/macos/arm64/1.3.6/OfferSteady-Companion-1.3.6-macOS-arm64.dmg', 'size': 126284123, 'sha256': 'dcc029f5d3c2c0073922ee91ad37a389eaf63b0dedf82050f736a05b95bfc0ad', 'contentType': 'application/x-apple-diskimage'}, {'key': 'desktop-releases/macos/x64/1.3.6/OfferSteady-Companion-1.3.6-macOS-x64.dmg', 'size': 129963799, 'sha256': '2b577117e6f8a02100b42e8e9e58fe2467242ce269286d1c1baa67940cd69ae8', 'contentType': 'application/x-apple-diskimage'}, {'key': 'desktop-releases/windows/x64/1.3.6/OfferSteady-Companion-Setup-1.3.6-Windows-x64.exe', 'size': 102172270, 'sha256': '18fd93b8d8c2ff412c0baea7a728eb392ba70962bae96a1f5bb27224ab811f54', 'contentType': 'application/vnd.microsoft.portable-executable'}]
CHUNK = 1024 * 1024

def verify(bucket):
    verified = 0
    for item in EXPECTED:
        head = bucket.head_object(item["key"])
        headers = {str(k).lower(): v for k, v in head.headers.items()}
        if int(head.content_length) != item["size"] or headers.get("content-type") != item["contentType"]:
            raise ValueError("object metadata mismatch")
        stream = bucket.get_object(item["key"])
        digest, size = hashlib.sha256(), 0
        try:
            while True:
                data = stream.read(CHUNK)
                if not data:
                    break
                digest.update(data)
                size += len(data)
                if size > item["size"]:
                    raise ValueError("object length overflow")
        finally:
            stream.close()
        if size != item["size"] or digest.hexdigest() != item["sha256"]:
            raise ValueError("object body mismatch")
        verified += 1
    return {"verified": verified, "ok": True}

def main():
    from app.core.config import Settings
    import oss2
    logging.getLogger("oss2").setLevel(logging.CRITICAL)
    s = Settings()
    if s.product_edition != "cn" or not all((s.oss_access_key_id, s.oss_access_key_secret, s.oss_bucket, s.oss_endpoint)):
        raise ValueError("storage unavailable")
    endpoint = str(s.oss_endpoint)
    if not endpoint.startswith(("https://", "http://")):
        endpoint = "https://" + endpoint
    bucket = oss2.Bucket(oss2.Auth(s.oss_access_key_id, s.oss_access_key_secret), endpoint, s.oss_bucket, connect_timeout=15)
    print(json.dumps(verify(bucket)))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(json.dumps({"ok": False, "reason": "object_verification_failed"}))
        raise SystemExit(1)
