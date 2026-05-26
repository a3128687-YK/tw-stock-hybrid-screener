from tw_stock_screener.scoring import fundamental_score, grade, stop_loss_reference


def test_grade_thresholds():
    assert grade(8.0) == "強勢觀察"
    assert grade(7.2) == "分批觀察"
    assert grade(5.0) == "等待回測"
    assert grade(4.9) == "排除"


def test_fundamental_score_caps():
    score = fundamental_score(
        {
            "revenue_yoy": 90,
            "roe": 26,
            "eps_last_4q": [1, 1.2, 1.5, 2.0],
            "pe": 12,
            "pe_3y_avg": 18,
        }
    )
    assert score == 30


def test_stop_loss_limits_atr_pct():
    text = stop_loss_reference({"price": 100, "atr": 10})
    assert "7.0%" in text

