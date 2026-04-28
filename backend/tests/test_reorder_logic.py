from app.services.reorder.reorder import ReorderService


def test_reorder_marks_critical_when_stock_is_zero():
    service = ReorderService(db=None)
    qty, reason, urgency = service._calculate_reorder(100, 0, 0, 20, 7)
    assert qty > 0
    assert urgency == "critical"
    assert "Immediate" in reason


def test_reorder_marks_high_when_stock_cover_is_low():
    service = ReorderService(db=None)
    qty, _, urgency = service._calculate_reorder(70, 20, 0, 20, 7)
    assert qty > 0
    assert urgency in {"critical", "high"}
