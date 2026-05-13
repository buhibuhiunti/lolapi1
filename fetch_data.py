import json
import time
import os
import sys
import urllib.request
import urllib.error


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
        "ru": "europe",
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
        encoded_name = urllib.parse.quote(game_name)
        encoded_tag = urllib.parse.quote(tag_line)
        data = self._get(
            f"/riot/account/v1/accounts/by-riot-id/{encoded_name}/{encoded_tag}",
            use_account=True
        )
        return data.get("puuid") if data else None

    def get_match_ids(self, puuid: str, count: int = 20, start: int = 0) -> list[str]:
        """PUUIDからマッチIDを取得 (v5)"""
        data = self._get(
            f"/lol/match/v5/matches/by-puuid/{puuid}/ids",
            {"start": start, "count": count}
        )
        if data:
            return data[:count]
        return []

    def get_match_detail(self, match_id: str) -> dict | None:
        return self._get(f"/lol/match/v5/matches/{match_id}")


def save_puuid_data(puuid: str, game_name: str, tag_line: str, output_path: str) -> None:
    """PUUIDデータをファイルに保存（リスト形式）"""
    new_entry = {
        "puuid": puuid,
        "game_name": game_name,
        "tag_line": tag_line,
    }
    
    puuids = load_puuids(output_path)
    
    # 重複チェック
    for p in puuids:
        if p["puuid"] == puuid:
            print(f"PUUIDは既に登録されています: {output_path}")
            return
    
    puuids.append(new_entry)
    
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(puuids, f, indent=2, ensure_ascii=False)
    print(f"PUUIDデータ保存: {output_path}")


def load_puuids(output_path: str) -> list:
    """保存されたPUUID一覧を読み込む"""
    if not os.path.exists(output_path):
        return []
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def load_puuid_data(file_path: str) -> dict | None:
    """保存されたPUUIDデータを読み込む"""
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_config(config_path: str) -> dict:
    """フィールド設定を読み込む"""
    if not os.path.exists(config_path):
        return None
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_enabled_fields(source: dict, config_section: dict) -> dict:
    """設定ファイルから有効なフィールドのみを抽出"""
    result = {}
    for field, enabled in config_section.items():
        if enabled and field in source:
            result[field] = source[field]
    return result


def extract_lane_matchup(raw_match: dict, config: dict) -> list[dict]:
    """同じレーンの対戦相手とのマッチアップを抽出 (v5対応, config適用)"""
    info = raw_match.get("info", {})
    participants = info.get("participants", [])
    matchups = []

    for p in participants:
        team = p.get("teamId", 0)

        # 敵陣営で同じレーンのプレイヤーを特定
        opponent = None
        for opp in participants:
            if opp.get("teamId", 0) != team and opp.get("lane", "") == p.get("lane", ""):
                opponent = opp
                break

        if not opponent:
            continue

        # configに基づいてフィールドを抽出
        match_data = extract_enabled_fields(info, config.get("match", {}))
        self_data = extract_enabled_fields(p, config.get("participant", {}))
        self_detail = extract_enabled_fields(p, config.get("participant_detail", {}))
        challenges = extract_enabled_fields(p.get("challenges", {}), config.get("challenges", {}).get("fields", {}))
        opp_data = extract_enabled_fields(opponent, config.get("opponent", {}))

        matchup = {
            "match": match_data,
            "self": {**self_data, **self_detail},
            "challenges": challenges if challenges else None,
            "opponent": opp_data,
        }

        # 空のセクションは削除
        matchup = {k: v for k, v in matchup.items() if v and v != {}}

        matchups.append(matchup)

    return matchups


def load_existing_data(output_path):
    """既存のデータをマージのために読み込む"""
    if not os.path.exists(output_path):
        return {}

    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    existing_ids = set()
    for matchup in data:
        game_id = matchup.get("match", {}).get("gameId")
        if game_id:
            existing_ids.add(str(game_id))

    return {"data": data, "existing_ids": existing_ids}


def fetch_lane_data(api_key: str, puuid: str, output_path: str, count: int = 20, region: str = "jp1", config_path: str = "data/config.json") -> None:
    """プレイヤーのマッチ履歴からレーン対戦データを取得"""
    config = load_config(config_path)
    if not config:
        print(f"config.json が見つかりません: {config_path}")
        return

    # 既存データを読み込む
    existing = load_existing_data(output_path)
    existing_data = existing["data"]
    existing_ids = existing["existing_ids"]

    fetcher = RiotFetcher(api_key, region)
    all_matchups = []
    new_match_count = 0
    duplicate_count = 0
    temp_path = output_path + ".tmp"

    # ページネーションでマッチIDを取得
    print(f"既存データ: {len(existing_data)}件 ({len(existing_ids)}マッチ)")
    print(f"目標取得数: {count}マッチ\n")

    batch_size = 100  # 一度に取得するマッチID数
    start_index = 0
    all_match_ids = []

    while len(all_match_ids) < count:
        remaining = count - len(all_match_ids)
        current_batch = min(batch_size, remaining)
        
        print(f"[ID取得] start={start_index}, count={current_batch}")
        batch_ids = fetcher.get_match_ids(puuid, current_batch, start_index)
        
        if not batch_ids:
            print(f"  -> さらに取得できるマッチIDはありません")
            break
        
        all_match_ids.extend(batch_ids)
        start_index += len(batch_ids)
        
        # APIレート制限対策 (2分間に100回 → 1.2秒/リクエスト)
        time.sleep(1.2)
        
        if len(batch_ids) < current_batch:
            print(f"  -> 残り取得可能: {len(batch_ids)}件 (全部取得済み)")
            break

    print(f"\nマッチID取得完了: {len(all_match_ids)}件\n")

    for i, mid in enumerate(all_match_ids):
        print(f"[詳細取得] {i + 1}/{len(all_match_ids)}: {mid}")
        raw = fetcher.get_match_detail(mid)

        if raw:
            # gameIdで重複チェック
            game_id = raw.get("info", {}).get("gameId")
            if str(game_id) in existing_ids:
                print(f"  -> 既に存在するマッチ (gameId: {game_id})")
                duplicate_count += 1
                continue

            matchups = extract_lane_matchup(raw, config)
            all_matchups.extend(matchups)
            new_match_count += 1

            # 途中保存
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(all_matchups, f, indent=2, ensure_ascii=False)

        time.sleep(1.2)

    print(f"\n[2/3] 抽出: {new_match_count}マッチ (重複: {duplicate_count})")

    # 既存データとマージ
    merged_data = existing_data + all_matchups

    # 最終保存
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged_data, f, indent=2, ensure_ascii=False)

    print(f"[3/3] 保存: {output_path} (合計: {len(merged_data)}件)")

    if os.path.exists(temp_path):
        os.remove(temp_path)

    print(f"\n完了 (新しい: {new_match_count}件, 重複: {duplicate_count}件)")


def load_field_descriptions(descriptions_path: str) -> dict:
    """フィールド説明文を読み込む"""
    if not os.path.exists(descriptions_path):
        return {}
    with open(descriptions_path, "r", encoding="utf-8") as f:
        return json.load(f)


def toggle_fields(config_path: str) -> None:
    """フィールドの有効/無効を対話的に切り替え"""
    config = load_config(config_path)
    if not config:
        print(f"config.json が見つかりません: {config_path}")
        return

    descriptions = load_field_descriptions("data/field_descriptions.json")

    print("\n=== フィールド設定編集 ===")
    print(f"現在の設定: {config_path}\n")

    while True:
        print("セクション選択:")
        print("  [1] match    - ゲーム情報")
        print("  [2] participant - プレイヤー基本情報")
        print("  [3] opponent  - 対戦相手情報")
        print("  [4] participant_detail - 詳細ステータス")
        print("  [5] challenges  - チャレンジ系")
        print("  [0] 終了\n")

        section = input("セクション: ").strip()

        if section == "0":
            break

        section_key = {"1": "match", "2": "participant", "4": "participant_detail", "5": "challenges"}.get(section, "opponent")
        if section == "3":
            section_key = "opponent"

        if section_key == "challenges":
            fields = config.get("challenges", {}).get("fields", {})
        else:
            fields = config.get(section_key, {})

        if not fields:
            print("このセクションにはフィールドがありません。\n")
            continue

        # 現在の状態を表示
        enabled = [k for k, v in fields.items() if v]
        print(f"\n[{section_key}] 有効: {len(enabled)}/{len(fields)}\n")

        while True:
            print("フィールド一覧 (0=戻る, *は有効):")
            for i, (key, value) in enumerate(fields.items(), 1):
                status = "*" if value else " "
                desc = descriptions.get(section_key, {}).get(key, "")
                desc_str = f" - {desc}" if desc else ""
                print(f"  {i}. {key} [{status}]{desc_str}")
            print()

            field_input = input("切り替え番号 (複数指定可, 空白=戻る): ").strip()
            if not field_input or field_input == "0":
                break

            # 複数指定対応 (スペース区切り)
            selections = field_input.split()
            for sel in selections:
                idx = int(sel) - 1
                field_name = list(fields.keys())[idx]
                fields[field_name] = not fields[field_name]
                desc = descriptions.get(section_key, {}).get(field_name, "")
                print(f"  {field_name} -> {'ON' if fields[field_name] else 'OFF'}{f' ({desc})' if desc else ''}")

    # 保存
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"\n保存完了: {config_path}")


if __name__ == "__main__":
    print("=== LoL レーン対戦データ取得ツール ===\n")
    print("[1] PUUID取得  [2] マッチ取得  [3] Match IDで取得  [4] チャンピオン一覧取得  [5] フィールド設定\n")

    mode = input("モード: ").strip()

    if mode == "5":
        config_path = "data/config.json"
        toggle_fields(config_path)

    elif mode == "4":
        api_key = input("APIキー: ").strip()
        print("\nチャンピオン一覧を取得しています...")
        url = "https://ddragon.leagueoflegends.com/cdn/14.10.1/data/en_US/champion.json"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        req.add_header('Accept', 'application/json')
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read())
                champions = data.get("data", {})
        except urllib.error.HTTPError as e:
            print(f"[ERROR] HTTP {e.code}")
            champions = None
        if champions:
            champion_list = []
            for cid, champ in champions.items():
                champion_list.append({
                    "id": int(champ["key"]),
                    "name": champ["name"],
                    "key": champ.get("key", ""),
                })
            champion_list.sort(key=lambda x: x["id"])
            os.makedirs("data", exist_ok=True)
            with open("data/champions.json", "w", encoding="utf-8") as f:
                json.dump(champion_list, f, indent=2, ensure_ascii=False)
            print(f"\n保存: data/champions.json ({len(champion_list)}チャンピオン)")
        else:
            print("チャンピオン一覧取得失敗")

    else:
        api_key = input("APIキー: ").strip()
        region_input = input("リージョン (jp1, kr, na1, etc.): ").strip() or "jp1"
        config_path = "data/config.json"

        if mode == "1":
            game_name = input("ゲーム名 (例: bro): ").strip()
            tag_line = input("タグ (例: han): ").strip()

            fetcher = RiotFetcher(api_key, region_input)
            puuid = fetcher.get_puuid(game_name, tag_line)
            if puuid:
                print(f"\nPUUID: {puuid}")
                save_puuid_data(puuid, game_name, tag_line, "data/puuids.json")
            else:
                print("PUUID取得失敗")

        elif mode == "2":
            # Load all available PUUIDs
            puuids = load_puuids("data/puuids.json")
            puuid_single = load_puuid_data("data/puuid.json")
            if puuid_single:
                puuids.append(puuid_single)
            
            if not puuids:
                print("data/puuids.json が見つかりません。モード1でPUUIDを先に取得してください。")
            else:
                print(f"\n利用可能なPUUID ({len(puuids)}件):")
                for i, p in enumerate(puuids, 1):
                    name = p.get("game_name", "?")
                    tag = p.get("tag_line", "?")
                    print(f"  [{i}] {name}/{tag}")
                print(f"  [0] 終了")
                
                choice = input("\nPUUID選択: ").strip()
                if choice == "0":
                    print("終了しました。")
                else:
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(puuids):
                            puuid = puuids[idx]["puuid"]
                            cnt = int(input("取得数 (default 20): ").strip() or "20")
                            fetch_lane_data(api_key, puuid, "data/lane_matchups.json", cnt, region_input, config_path)
                        else:
                            print("無効な選択です。")
                    except ValueError:
                        print("無効な入力です。")

        elif mode == "3":
            ids = input("Match IDをスペース区切り: ").split()
            config = load_config(config_path)
            if not config:
                print(f"config.json が見つかりません: {config_path}")
            else:
                fetcher = RiotFetcher(api_key, region_input)
                all_matchups = []

                for mid in ids:
                    print(f"取得中: {mid}")
                    raw = fetcher.get_match_detail(mid)
                    if raw:
                        all_matchups.extend(extract_lane_matchup(raw, config))
                    time.sleep(1.2)

                os.makedirs("data", exist_ok=True)
                with open("data/lane_matchups.json", "w", encoding="utf-8") as f:
                    json.dump(all_matchups, f, indent=2, ensure_ascii=False)

                print(f"\n保存: data/lane_matchups.json ({len(all_matchups)}レーン対戦)")

        else:
            print("無効な選択")
