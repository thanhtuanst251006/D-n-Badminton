"""Public shop listings, with provenance and no imputed prices/specifications."""

import argparse
import json
import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

from racket_rec.cleaning import clean_balance, clean_stiffness, clean_weight

ROOT = Path(__file__).resolve().parents[2]
FEATURES = ["weight_g", "balance_score", "stiffness_score"]


@dataclass(frozen=True)
class Shop:
    name: str
    category_url: str
    card: str
    title: str
    price: str

    def page_url(self, page: int) -> str:
        if page == 1:
            return self.category_url
        if self.name == "ShopVNB":
            return f"{self.category_url}?page={page}"
        return f"{self.category_url}page/{page}/"


SHOPS = {
    "ShopVNB": Shop(
        "ShopVNB",
        "https://shopvnb.com/vot-cau-long.html",
        ".item_product_main",
        ".product-name a",
        ".price-box .price",
    ),
    "FBShop": Shop(
        "FBShop",
        "https://fbshop.vn/vot-cau-long/",
        ".prd-card",
        ".prd-card-link",
        ".price-current",
    ),
    "HVShop": Shop(
        "HVShop",
        "https://hvshop.vn/vot-cau-long/",
        "div.product.type-product",
        ".product-title a",
        ".price",
    ),
}

BRANDS = {
    "yonex": "Yonex",
    "li ning": "Li-Ning",
    "lining": "Li-Ning",
    "victor": "Victor",
    "mizuno": "Mizuno",
    "vnb": "VNB",
    "kumpoo": "Kumpoo",
    "apacs": "Apacs",
    "proace": "Proace",
    "felet": "Felet",
    "fleet": "Fleet",
    "kawasaki": "Kawasaki",
    "vicleo": "VicLeo",
    "hundred": "Hundred",
    "vs": "VS",
    "adidas": "Adidas",
    "flypower": "Flypower",
    "gosen": "Gosen",
    "redson": "Redson",
    "kamito": "Kamito",
    "the 3rd game": "The 3rd Game",
    "forza": "Forza",
    "tenway": "Tenway",
    "protech": "Protech",
    "jogarbola": "Jogarbola",
    "ixe": "IXE",
    "maxta": "Maxta",
    "ashaway": "Ashaway",
    "babolat": "Babolat",
    "wilson": "Wilson",
    "kizuna": "Kizuna",
    "kaiwin": "Kaiwin",
    "taro": "Taro",
}


def plain(text: str) -> str:
    value = unicodedata.normalize("NFKD", text.casefold().replace("đ", "d"))
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def brand_from_title(title: str) -> str:
    text = f" {plain(title)} "
    for alias, brand in BRANDS.items():
        if f" {alias} " in text:
            return brand
    return "Khác / chưa rõ"


def parse_price(text: str) -> tuple[int | None, int | None, str]:
    """Preserve ranges, omit contact-only prices, and never concatenate numbers."""
    if not text or any(word in plain(text) for word in ["lien he", "het hang"]):
        return None, None, "contact"
    values = re.findall(
        r"(?<!\d)\d{1,3}(?:[.,]\d{3})+(?!\d)|(?<![\d.,])\d{4,}(?![\d.,])", text
    )
    prices = [int(re.sub(r"\D", "", v)) for v in values]
    prices = [p for p in prices if p > 0]
    if not prices:
        return None, None, "contact"
    kind = "range" if len(set(prices)) > 1 else "exact"
    if plain(text).startswith("tu "):
        kind = "from"
    return min(prices), max(prices), kind


def normalize_specs(row: dict) -> dict:
    """Only normalize explicit shop values; ambiguous weight classes stay unknown."""
    raw_weight = str(row["weight_raw"]) if pd.notna(row.get("weight_raw")) else ""
    classes = set(re.findall(r"\b[2-7]U\b", raw_weight.upper()))
    row["weight_g"] = (
        clean_weight(raw_weight) if len(classes) <= 1 and raw_weight else None
    )
    row["balance_score"] = clean_balance(row.get("balance_raw"))
    row["stiffness_score"] = clean_stiffness(row.get("stiffness_raw"))
    row["specs_complete"] = all(pd.notna(row.get(f)) for f in FEATURES)
    row["imputation_reason"] = (
        "Thông số do shop công bố; trọng lượng U được quy đổi theo nhóm, điểm 1–5 là quy đổi gần đúng"
        if row["specs_complete"]
        else "Chưa đủ thông số công bố để chấm điểm; không tự điền khuyết"
    )
    return row


def parse_listing(html: str, shop: Shop, collected_at: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    seen = set()
    for card in soup.select(shop.card):
        anchor = card.select_one(shop.title)
        if anchor is None:
            continue
        title = anchor.get_text(" ", strip=True)
        normalized_title = plain(title)
        if "vot" not in normalized_title or any(
            word in normalized_title
            for word in ["combo", "cap vot", "set vot", "training", "vot tap"]
        ):
            continue
        url = (
            urljoin(shop.category_url, anchor.get("href", ""))
            .split("#")[0]
            .split("?")[0]
        )
        if (
            urlparse(url).netloc != urlparse(shop.category_url).netloc
            or urlparse(url).scheme != "https"
            or url in seen
        ):
            continue
        price_el = card.select_one(shop.price)
        if shop.name == "FBShop" and price_el is None:
            price_el = card.select_one(".prd-card-price")
        if price_el is not None:
            # WooCommerce puts the current price in <ins>, before the crossed-out price in DOM order.
            current = price_el.select_one("ins")
            if current is not None:
                price_el = current
            else:
                for old in price_el.select("del, .screen-reader-text, .price-old"):
                    old.decompose()
        price_text = price_el.get_text(" ", strip=True) if price_el else "Liên hệ"
        minimum, maximum, kind = parse_price(price_text)
        model = re.sub(r"^vợt\s+cầu\s+lông\s*", "", title, flags=re.IGNORECASE).strip()
        row = {
            "title": title,
            "brand": brand_from_title(title),
            "model": model,
            "price_vnd": minimum,
            "price_max_vnd": maximum,
            "price_text": price_text,
            "price_kind": kind,
            "source": shop.name,
            "product_url": url,
            "collected_at": collected_at,
            "data_kind": "real",
            "weight_raw": None,
            "balance_raw": None,
            "stiffness_raw": None,
            "availability": "Shop ghi hết hàng"
            if "outofstock" in card.get("class", [])
            else "Cần kiểm tra tại shop",
        }
        if shop.name == "HVShop":
            attrs = [a.get_text(" ", strip=True) for a in card.select(".attr-item")]
            if len(attrs) >= 3:
                row.update(
                    stiffness_raw=attrs[0], balance_raw=attrs[1], weight_raw=attrs[2]
                )
        rows.append(normalize_specs(row))
        seen.add(url)
    return rows


def parse_detail_specs(html: str) -> dict:
    """Extract labelled table rows / paragraphs, never specs from related products."""
    soup = BeautifulSoup(html, "html.parser")
    result = {}
    labels = {
        "trong luong": "weight_raw",
        "diem can bang": "balance_raw",
        "do cung": "stiffness_raw",
    }
    for element in soup.select("tr, .mona-content p, .prddt p"):
        cells = element.select("th, td")
        if len(cells) >= 2:
            label, value = (
                cells[0].get_text(" ", strip=True),
                cells[1].get_text(" ", strip=True),
            )
        else:
            text = element.get_text(" ", strip=True)
            if ":" not in text:
                continue
            label, value = text.split(":", 1)
        label = plain(label)
        if len(label) > 40 or not value.strip():
            continue
        for prefix, field in labels.items():
            if label.startswith(prefix):
                result.setdefault(field, value.strip())
    return result


def fetch_html(session: requests.Session, url: str) -> str:
    response = session.get(url, timeout=(8, 25))
    response.raise_for_status()
    if urlparse(response.url).netloc != urlparse(url).netloc:
        raise ValueError("Shop redirected to a different domain")
    response.encoding = "utf-8"
    return response.text


def collect_shop(
    shop: Shop, pages: int, details: int, delay: float
) -> tuple[list[dict], dict]:
    rows = {}
    errors = []
    now = datetime.now(UTC).isoformat(timespec="seconds")
    with requests.Session() as session:
        session.headers.update(
            {"User-Agent": "RacketPro/1.0 (public product catalog; low-rate requests)"}
        )
        for page in range(1, pages + 1):
            try:
                found = parse_listing(
                    fetch_html(session, shop.page_url(page)), shop, now
                )
                fresh = [r for r in found if r["product_url"] not in rows]
                if not fresh:
                    errors.append(
                        f"Trang {page}: không có sản phẩm mới; dừng phân trang"
                    )
                    break
                rows.update({r["product_url"]: r for r in fresh})
            except (requests.RequestException, ValueError) as exc:
                errors.append(f"Trang {page}: {exc}")
                break
            time.sleep(delay)
        for row in list(rows.values())[:details]:
            if row["specs_complete"]:
                continue
            try:
                specs = parse_detail_specs(fetch_html(session, row["product_url"]))
                row.update(specs)
                normalize_specs(row)
            except (requests.RequestException, ValueError) as exc:
                errors.append(f"Thông số {row['model']}: {exc}")
            time.sleep(delay)
    return list(rows.values()), {
        "shop": shop.name,
        "collected_at": now,
        "offers": len(rows),
        "errors": errors,
    }


def collect_catalog(
    pages: int = 10, details: int = 25, delay: float = 0.5
) -> tuple[pd.DataFrame, list[dict]]:
    # At most one worker per shop; every shop has its own sequential request queue.
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(
            pool.map(
                lambda shop: collect_shop(shop, pages, details, delay), SHOPS.values()
            )
        )
    rows = [row for shop_rows, _ in results for row in shop_rows]
    return pd.DataFrame(rows), [status for _, status in results]


def save_snapshot(catalog: pd.DataFrame, status: list[dict], directory: Path) -> None:
    """Keep last good rows for failed shops instead of replacing everything with empty data."""
    path = directory / "shop_offers.csv"
    if path.exists():
        previous = pd.read_csv(path)
        successful = set(catalog["source"]) if not catalog.empty else set()
        failed = {entry["shop"] for entry in status if entry.get("errors")}
        keep = ~previous["source"].isin(successful - failed)
        if not catalog.empty and "product_url" in catalog and "product_url" in previous:
            keep &= ~previous["product_url"].isin(catalog["product_url"])
        catalog = pd.concat([catalog, previous[keep]], ignore_index=True)
    if catalog.empty:
        raise ValueError("Không lấy được sản phẩm nào; giữ nguyên dữ liệu cũ")
    directory.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    catalog.to_csv(temporary, index=False, encoding="utf-8-sig")
    temporary.replace(path)
    (directory / "shop_status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_snapshot(directory: Path = ROOT / "data/processed") -> pd.DataFrame:
    path = directory / "shop_offers.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    for field in ["price_vnd", "price_max_vnd", *FEATURES]:
        df[field] = pd.to_numeric(df[field], errors="coerce")
    df["specs_complete"] = df[FEATURES].notna().all(axis=1)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cập nhật danh mục công khai từ ShopVNB, FBShop, HVShop"
    )
    parser.add_argument("--pages", type=int, default=10)
    parser.add_argument("--details", type=int, default=25)
    args = parser.parse_args()
    if not 1 <= args.pages <= 20 or not 0 <= args.details <= 100:
        parser.error("--pages: 1–20; --details: 0–100 (mỗi shop)")
    catalog, status = collect_catalog(args.pages, args.details)
    save_snapshot(catalog, status, ROOT / "data/processed")
    print(json.dumps(status, ensure_ascii=False, indent=2))
    print(
        f"Đã ghi nhận {len(catalog)} chào bán thật; giá có thể đổi sau thời điểm lấy dữ liệu."
    )


if __name__ == "__main__":
    main()
