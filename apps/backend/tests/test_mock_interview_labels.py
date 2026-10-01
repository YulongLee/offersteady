from unittest.mock import Mock

import pytest

from app.services.mock_interview_repository import MockInterviewRepository


@pytest.mark.parametrize("kind,points,label", [
    ("mock_interview_entry_settlement", -100, "模拟面试创建"),
    ("mock_interview_minute_settlement", -5, "模拟面试分钟费"),
    ("mock_interview_refund", 100, "模拟面试故障退还"),
    ("pass_usage", 0, "模拟面试每日会员免费权益"),
])
def test_new_ledger_labels_do_not_change_billing_identifiers_or_amounts(kind, points, label):
    cursor = Mock()
    MockInterviewRepository._ledger(cursor, user_id="synthetic-owner", session_id="synthetic-session",
        kind=kind, points=points, reference="synthetic-reference", now_ms=123)
    cursor.execute.assert_called_once()
    sql, params = cursor.execute.call_args.args
    assert "ON CONFLICT (reference_id) DO NOTHING" in sql
    assert params[1:] == ("synthetic-owner", kind, points, 123, "synthetic-reference", label)
