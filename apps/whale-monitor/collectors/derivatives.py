"""파생상품 지표 수집기 — 1분 폴링 (OI, 펀딩비, 롱숏비율)."""
import logging
import requests

logger = logging.getLogger(__name__)

OI_URL = "https://fapi.binance.com/fapi/v1/openInterest"
FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
LS_RATIO_URL = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"


def collect_derivatives(conn, state, symbol):
    """OI, 펀딩비, 롱숏비율 수집 → state 업데이트."""
    try:
        # OI
        oi_resp = requests.get(OI_URL, params={"symbol": symbol}, timeout=10)
        oi_resp.raise_for_status()
        oi_data = oi_resp.json()
        current_oi = float(oi_data["openInterest"])

        # OI 변화율 계산
        oi_change_pct = None
        if state["oi_history"]:
            prev_oi = state["oi_history"][-1]["oi"]
            if prev_oi > 0:
                oi_change_pct = (current_oi - prev_oi) / prev_oi * 100

        state["oi_history"].append({"oi": current_oi, "change_pct": oi_change_pct})

        # 펀딩비
        try:
            fund_resp = requests.get(
                FUNDING_URL, params={"symbol": symbol, "limit": 1}, timeout=10
            )
            fund_resp.raise_for_status()
            fund_data = fund_resp.json()
            if fund_data:
                current_funding = float(fund_data[-1]["fundingRate"])
                prev_funding = state.get("last_funding")
                funding_delta = None
                if prev_funding is not None:
                    funding_delta = current_funding - prev_funding
                state["last_funding"] = current_funding
                state["last_funding_delta"] = funding_delta
        except Exception as e:
            logger.warning(f"펀딩비 수집 오류: {e}")

        # 롱숏비율
        try:
            ls_resp = requests.get(
                LS_RATIO_URL,
                params={"symbol": symbol, "period": "5m", "limit": 1},
                timeout=10,
            )
            ls_resp.raise_for_status()
            ls_data = ls_resp.json()
            if ls_data:
                state["last_ls_ratio"] = float(ls_data[-1]["longShortRatio"])
        except Exception as e:
            logger.warning(f"롱숏비율 수집 오류: {e}")

        logger.debug(
            f"파생 수집: OI={current_oi:.2f} change={oi_change_pct or 'N/A'}"
        )

    except Exception as e:
        logger.error(f"파생상품 수집 오류: {e}")
