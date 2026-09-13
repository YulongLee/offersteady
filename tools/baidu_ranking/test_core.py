import io
import json
from urllib.error import HTTPError

from .core import BaiduRankingClient, RankingConfig, run_queries, write_reports


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = json.dumps(payload, ensure_ascii=False).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.payload


def test_missing_credentials_never_calls_provider():
    calls = []
    client = BaiduRankingClient(RankingConfig(app_code=None, access_key=None, secret_key=None), opener=lambda *args, **kwargs: calls.append(args))
    result = client.query("AI面试助手")
    assert result.safe_error_code == "missing_credentials"
    assert calls == []


def test_rank_label_is_preserved_and_capped_at_50():
    payload = {"code": 200, "success": True, "data": {"Ranks": [{"RankStr": "3-2", "Title": "首页", "Url": "https://mianshiwen.cn/"}] * 60}}
    result = BaiduRankingClient(RankingConfig(app_code="secret"), opener=lambda *args, **kwargs: FakeResponse(payload)).query("AI面试助手")
    assert result.status == "ranked"
    assert result.rank_label == "3-2"
    assert len(result.results) == 50


def test_not_found_is_not_zero_rank():
    result = BaiduRankingClient(RankingConfig(app_code="secret"), opener=lambda *args, **kwargs: FakeResponse({"code": 200, "success": True, "data": {"Ranks": []}})).query("不存在")
    assert result.status == "not_found"
    assert result.rank_label is None


def test_batch_requires_explicit_confirmation():
    config = RankingConfig(app_code="secret")
    try:
        run_queries(config, ["a", "b"])
    except ValueError as exc:
        assert str(exc) == "batch_confirmation_required"
    else:
        raise AssertionError("batch mode was not gated")


def test_reports_do_not_contain_credentials(tmp_path):
    result = BaiduRankingClient(RankingConfig(app_code="DO_NOT_PRINT"), opener=lambda *args, **kwargs: FakeResponse({"code": 200, "success": True, "data": {"Ranks": []}})).query("AI面试助手")
    paths = write_reports([result], tmp_path, formats={"json", "markdown"})
    content = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    assert "DO_NOT_PRINT" not in content
    assert "authorization" not in content.lower()
