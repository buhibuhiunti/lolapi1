import json
import os
import sys
import time


def fetch_champion_stats(patch: str = "", tier: str = "") -> list[dict]:
    """Poro Data Store (GitHub) から全チャンピオン統計を取得"""
    import urllib.request
    import urllib.error

    # Poro Data Store のチャンピオン統計JSON
    base = "https://raw.githubusercontent.com/poro-data-store/poro-data-store/master/data/champion-statistics"

    params = []
    if patch:
        params.append(f"patch={patch}")
    if tier:
        params.append(f"tier={tier}")

    query = "&".join(params)
    url = f"{base}?{query}" if query else base

    print(f"取得中: {url}\n")

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"[ERROR] HTTP {e.code}: {e.reason}")
        if e.code == 429:
            print("レート制限。3秒待機して再試行...")
            time.sleep(3)
        return []
    except Exception as e:
        print(f"[ERROR] {e}")
        return []


def fetch_patch_stats(patch: str = "") -> dict:
    """パッチ別統計を取得"""
    import urllib.request

    base = "https://od-api.sgg.me/statistics/parts"

    if patch:
        base += f"?patch={patch}"

    try:
        req = urllib.request.Request(base)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"[ERROR] {e}")
        return {}


def save_stats(stats: list[dict], output_path: str) -> None:
    """統計データを保存（必要なフィールドのみ抽出）"""
    extracted = []
    for champ in stats:
        extracted.append({
            "name": champ.get("name", ""),
            "id": champ.get("id", 0),
            "patch": champ.get("patch", ""),
            "games": champ.get("games", 0),
            "wins": champ.get("wins", 0),
            "losses": champ.get("losses", 0),
            "win_rate": champ.get("win_rate", 0) * 100,
            "tier": champ.get("tier", ""),
            "role": champ.get("role", ""),
        })

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(extracted, f, indent=2, ensure_ascii=False)

    print(f"保存: {output_path} ({len(extracted)}チャンピオン)")


if __name__ == "__main__":
    print("=== 全チャンピオン勝率取得 (od-api) ===\n")

    patch = input("パッチ (空=current): ").strip()
    region = input("リージョン (default=JP): ").strip() or "JP"
    tier = input("ティア (空=all): ").strip()

    stats = fetch_champion_stats(patch, region, tier)

    if not stats:
        print("データ取得失敗。APIが一時的に利用できない可能性があります。")
        sys.exit(1)

    save_stats(stats, "data/champion_stats.json")

    print(f"\n合計: {len(stats)}チャンピオン")