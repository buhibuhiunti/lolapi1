import json
import time
import os
import sys


class RiotFetcher:
    """Riot公式APIからマッチデータを取得"""

    # 地域ルータリングマッピング
    ROUTING_MAP = {
        "jp1": "asia",
        "kr": "asia",
        "tw2": "asia",
        "th2": "asia",
        "sg2": "asia",
        "ph2": "asia",
        "vn2": "asia",
        "na1": "americas",
        "br1": "americas",
        "la1": "americas",
        "la2": "americas",
        "am1": "americas",
        "euw1": "europe",
        "eun1": "europe",
        "oc1": "oce",
    }

    def __init__(self, api_key: str, region: str = "jp1"):
        self.api_key = api_key
        self.region = region
        routing = self.ROUTING_MAP.get(region, region)
        self.account_base = "https://{}.api.riotgames.com".format(routing)
        self.match_base = "https://{}.api.riotgames.com".format(routing)

    def _get(self, endpoint: str, params: dict = None, use_account: bool = False) -> dict | None:
        import urllib.request
        import urllib.error
        import urllib.parse

        # PUUIDの特殊文字をURLエンコーディング
        if params is None:
            params = {}
        params["api_key"] = self.api_key

        # URLに ? があれば & で、なければ ? で結合
        separator = "&" if "?" in endpoint else "?"
        query = urllib.parse.urlencode(params)

        # Accountエンドポイントは地域ルーティングを使用
        base = self.account_base if use_account else self.match_base
        url = f"{base}{endpoint}{separator}{query}"

        print(f"  -> {url}")

        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            req.add_header('Accept', 'application/json')
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8')
            print(f"[ERROR] HTTP {e.code}: {e.reason}")
            print(f"  URL: {url}")
            print(f"  Response: {body}")
            return None

    def get_puuid(self, game_name: str, tag_line: str) -> str | None:
        """Riot ID (ゲーム名/タグ) からPUUIDを取得"""
        data = self._get(
            f"/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}",
            use_account=True
        )
        return data.get("puuid") if data else None

    def get_match_ids(self, puuid: str, count: int = 20) -> list[str]:
        """PUUIDからマッチIDを取得 (v5)"""
        data = self._get(
            f"/lol/match/v5/matches/by-puuid/{puuid}/ids",
            {"start": 0, "count": count}
        )
        if data:
            return data[:count]
        return []

    def get_match_detail(self, match_id: str) -> dict | None:
        return self._get(f"/lol/match/v5/matches/{match_id}")


def extract_lane_matchup(raw_match: dict) -> list[dict]:
    """同じレーンの対戦相手とのマッチアップを抽出 (v5対応)"""
    mid = raw_match.get("metadata", {}).get("matchId", "")
    dur = raw_match.get("info", {}).get("gameDuration", 0)
    dur_min = round(dur / 60, 2)

    participants = raw_match.get("info", {}).get("participants", [])
    matchups = []

    for p in participants:
        # 自分の情報 (v5ではchampionNameはなくchampionIdのみ)
        champ_id = p.get("championId", 0)
        lane = p.get("lane", "")
        team = p.get("teamId", 0)
        win = p.get("win", False)
        summoner_id = p.get("summonerId", "")

        # 敵陣営で同じレーンのプレイヤーを特定
        for opp in participants:
            if opp.get("teamId", 0) != team and opp.get("lane", "") == lane:
                matchups.append({
                    "match_id": mid,
                    "summoner_id": summoner_id,
                    "champion_id": champ_id,
                    "opponent_id": opp.get("championId", 0),
                    "lane": lane,
                    "duration_min": dur_min,
                    "win": win,
                })

    return matchups


def fetch_lane_data(api_key: str, puuid: str, output_path: str, count: int = 20, region: str = "jp1") -> None:
    """プレイヤーのマッチ履歴からレーン対戦データを取得"""
    fetcher = RiotFetcher(api_key, region)
    all_matchups = []
    temp_path = output_path + ".tmp"

    match_ids = fetcher.get_match_ids(puuid, count)
    print(f"マッチID取得: {len(match_ids)}件\n")

    for i, mid in enumerate(match_ids):
        print(f"[1/3] 取得中 {i + 1}/{len(match_ids)}: {mid}")
        raw = fetcher.get_match_detail(mid)

        if raw:
            matchups = extract_lane_matchup(raw)
            all_matchups.extend(matchups)

            # 途中保存
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(all_matchups, f, indent=2, ensure_ascii=False)

        time.sleep(0.6)

    print(f"\n[2/3] 抽出: {len(all_matchups)}レーン対戦")

    # 最終保存
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_matchups, f, indent=2, ensure_ascii=False)

    print(f"[3/3] 保存: {output_path}")

    if os.path.exists(temp_path):
        os.remove(temp_path)

    print("\n完了")


if __name__ == "__main__":
    print("=== LoL レーン対戦データ取得ツール ===\n")
    print("[1] Summoner名で取得  [2] PUUIDで取得  [3] Match IDで取得\n")

    mode = input("モード: ").strip()

    # リージョン入力共通
    region_input = input("リージョン (jp1, kr, na1, etc.): ").strip() or "jp1"

    if mode == "1":
        api_key = input("APIキー: ").strip()
        game_name = input("ゲーム名 (例: bro): ").strip()
        tag_line = input("タグ (例: han): ").strip()
        cnt = int(input("取得数 (default 20): ").strip() or "20")

        fetcher = RiotFetcher(api_key, region_input)
        puuid = fetcher.get_puuid(game_name, tag_line)
        if puuid:
            print(f"\nPUUID: {puuid}")
            fetch_lane_data(api_key, puuid, "data/lane_matchups.json", cnt, region_input)
        else:
            print("PUUID取得失敗")

    elif mode == "2":
        api_key = input("APIキー: ").strip()
        puuid = input("PUUID: ").strip()
        cnt = int(input("取得数 (default 20): ").strip() or "20")
        fetch_lane_data(api_key, puuid, "data/lane_matchups.json", cnt, region_input)

    elif mode == "3":
        api_key = input("APIキー: ").strip()
        ids = input("Match IDをスペース区切り: ").split()

        fetcher = RiotFetcher(api_key, region_input)
        all_matchups = []

        for mid in ids:
            print(f"取得中: {mid}")
            raw = fetcher.get_match_detail(mid)
            if raw:
                all_matchups.extend(extract_lane_matchup(raw))
            time.sleep(0.6)

        os.makedirs("data", exist_ok=True)
        with open("data/lane_matchups.json", "w", encoding="utf-8") as f:
            json.dump(all_matchups, f, indent=2, ensure_ascii=False)

        print(f"\n保存: data/lane_matchups.json ({len(all_matchups)}レーン対戦)")

    else:
        print("無効な選択")
