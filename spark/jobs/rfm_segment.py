"""Pure RFM segment classification logic (no Spark dependency)."""


def classify_rfm(r: int, f: int, m: int) -> str:
    """Classify RFM scores into segments.

    Rules (evaluated in order, first match wins):
        VIP:     R >= 4 AND F >= 4 AND M >= 4
        Loyal:   F >= 3
        Risk:    R <= 2
        New:     R >= 4 AND F <= 2
        Regular: everything else
    """
    if r >= 4 and f >= 4 and m >= 4:
        return "VIP"
    if f >= 3:
        return "Loyal"
    if r <= 2:
        return "Risk"
    if r >= 4 and f <= 2:
        return "New"
    return "Regular"
