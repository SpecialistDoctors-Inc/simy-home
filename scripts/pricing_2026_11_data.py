"""Public November pricing data shared by announcement and service pages."""
import re

RECURRING = (
    "base", "hearing_8h", "hearing_20h", "fp_quality", "sqm_check",
    "land_valuation", "homepage", "homepage_secure", "homepage_ops",
)
PENDING = {
    "drawing_quote": "提供開始と込み枚数の確定後",
    "drawing_overage": "提供開始と超過料金の確定後",
    "storage_100gb": "販売条件の確定後",
    "storage_1tb": "販売条件の確定後",
}
USAGE = (
    "hearing_bot", "hearing_overage", "transcription_20h", "transcription_overage",
    "land_valuation_overage", "homepage_transfer_overage", "homepage_request_overage",
    "homepage_secure_request_overage", "homepage_ops_overage",
)


def parse_prices(spec):
    rows = {}
    for line in spec.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `"):
            continue
        code, name, unit, usd, jpy, included, overage = [part.strip() for part in line.split("|")[1:-1]]
        code = code.strip("`")
        if code in rows:
            raise ValueError(f"Duplicate pricing code: {code}")
        row = {"name": name, "unit": unit, "included": included, "overage": overage}
        if code != "enterprise":
            for currency, cell in (("jpy", jpy), ("usd", usd)):
                match = re.fullmatch(r"(\d+)(?:（年払い (\d+)/月＝(\d+)/年）)?", cell)
                if not match:
                    raise ValueError(f"Unrecognized {currency} price for {code}: {cell}")
                amount, equivalent, annual = match.groups()
                row[currency] = int(amount)
                if annual:
                    if int(equivalent) * 12 != int(annual):
                        raise ValueError(f"Inconsistent annual price for {code}")
                    row[f"{currency}_annual"] = int(annual)
        rows[code] = row
    expected = set(RECURRING) | set(USAGE) | set(PENDING) | {"enterprise"}
    if rows.keys() != expected:
        raise ValueError(f"Unclassified pricing codes: {sorted(rows.keys() ^ expected)}")
    if {code for code, row in rows.items() if "jpy_annual" in row} != {"base", "sqm_check"}:
        raise ValueError("Annual price eligibility changed")
    if any(("jpy_annual" in row) != ("usd_annual" in row) for row in rows.values()):
        raise ValueError("Annual price is missing in one currency")
    return rows


def money(amount, currency):
    if currency == "jpy":
        return f"¥{amount:,}"
    dollars = amount / 100
    return f"${dollars:,.2f}".removesuffix(".00")
