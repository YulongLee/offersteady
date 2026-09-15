from types import SimpleNamespace

from app.services.baidu_ranking import BaiduRankingClient


def test_baidu_client_normalizes_rank_results(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"code": 200, "data": {"Ranks": [{"RankStr": "2-3", "Title": "首页", "Url": "https://mianshiwen.cn/"}]}}

    captured = {}

    def fake_post(url, **kwargs):
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr("app.services.baidu_ranking.httpx.post", fake_post)
    settings = SimpleNamespace(
        baidu_ranking_enabled=True,
        baidu_ranking_endpoint="https://example.test/rank",
        baidu_ranking_access_key="ak",
        baidu_ranking_secret_key="sk",
        baidu_ranking_app_code=None,
        baidu_ranking_timeout_seconds=3,
        baidu_ranking_retry_attempts=0,
    )
    result = BaiduRankingClient(settings).query(domain="mianshiwen.cn", keyword="AI面试助手")
    assert result["status"] == "ranked"
    assert result["results"] == [{"rank": 3, "title": "首页", "url": "https://mianshiwen.cn/"}]
    assert captured["data"] == {"domain": "mianshiwen.cn", "keyword": "AI面试助手"}
    assert "ak" not in str(result) and "sk" not in str(result)


def test_baidu_client_limits_results_to_fifty(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": {"Ranks": [{"RankStr": f"1-{i}"} for i in range(1, 60)]}}

    monkeypatch.setattr("app.services.baidu_ranking.httpx.post", lambda *args, **kwargs: Response())
    settings = SimpleNamespace(
        baidu_ranking_enabled=True,
        baidu_ranking_endpoint="https://example.test/rank",
        baidu_ranking_access_key="ak",
        baidu_ranking_secret_key="sk",
        baidu_ranking_app_code=None,
        baidu_ranking_timeout_seconds=3,
        baidu_ranking_retry_attempts=0,
    )
    result = BaiduRankingClient(settings).query(domain="mianshiwen.cn", keyword="关键词")
    assert len(result["results"]) == 50
