"""RFM segment classification boundary-value tests."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "spark", "jobs"))

from rfm_segment import classify_rfm


# --- VIP: R>=4 AND F>=4 AND M>=4 ---

def test_vip_all_max():
    assert classify_rfm(5, 5, 5) == "VIP"

def test_vip_boundary():
    assert classify_rfm(4, 4, 4) == "VIP"

def test_vip_fails_low_r():
    """R=3 breaks VIP condition -> falls to Loyal (F>=4 >= 3)."""
    assert classify_rfm(3, 4, 4) == "Loyal"

def test_vip_fails_low_f():
    """F=3 breaks VIP -> Loyal (F>=3)."""
    assert classify_rfm(4, 3, 4) == "Loyal"

def test_vip_fails_low_m():
    """M=3 breaks VIP -> Loyal (F>=4 >= 3)."""
    assert classify_rfm(4, 4, 3) == "Loyal"


# --- Loyal: F>=3 (checked after VIP) ---

def test_loyal_typical():
    assert classify_rfm(3, 3, 2) == "Loyal"

def test_loyal_high_f_low_r():
    """F=5 but R=2 -> Loyal wins over Risk because Loyal is checked first."""
    assert classify_rfm(2, 5, 5) == "Loyal"

def test_loyal_boundary_f3():
    assert classify_rfm(3, 3, 3) == "Loyal"


# --- Risk: R<=2 (checked after Loyal) ---

def test_risk_low_r_low_f():
    """R=1, F=1 -> not Loyal (F<3) -> Risk."""
    assert classify_rfm(1, 1, 5) == "Risk"

def test_risk_r2_f2():
    assert classify_rfm(2, 2, 5) == "Risk"

def test_risk_boundary_r2():
    assert classify_rfm(2, 1, 1) == "Risk"


# --- New: R>=4 AND F<=2 ---

def test_new_typical():
    assert classify_rfm(4, 2, 2) == "New"

def test_new_high_r_low_f():
    assert classify_rfm(5, 1, 1) == "New"

def test_new_boundary():
    assert classify_rfm(4, 2, 1) == "New"


# --- Regular: everything else ---

def test_regular_mid_scores():
    assert classify_rfm(3, 2, 3) == "Regular"

def test_regular_r3_f2_m5():
    assert classify_rfm(3, 2, 5) == "Regular"
