import json
import os


def load_data(data_path):
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_champion_input(input_str):
    """チャンピオン名またはIDからchampion_idを取得"""
    if not input_str:
        return None

    champions_path = os.path.join(os.path.dirname(__file__), "data", "champions.json")
    champions = load_data(champions_path)

    lower_input = input_str.lower()

    for champ in champions:
        if str(champ["id"]) == input_str:
            return champ["id"]
        if champ["name"].lower() == lower_input:
            return champ["id"]
        if champ.get("key", "").lower() == lower_input:
            return champ["id"]

    print(f"チャンピオンが見つかりません: {input_str}")
    return None


def filter_matchups(matchups, filters):
    """フィルタ条件でマッチデータをフィルタリング"""
    results = matchups

    if filters.get("puuid"):
        results = [m for m in results if m.get("self", {}).get("puuid") == filters["puuid"]]
    if filters.get("champion_id"):
        results = [m for m in results if m.get("self", {}).get("championId") == filters["champion_id"]]
    if filters.get("queue_id"):
        results = [m for m in results if m.get("match", {}).get("queueId") == filters["queue_id"]]
    if filters.get("position"):
        results = [m for m in results if m.get("self", {}).get("teamPosition") == filters["position"]]

    return results


def display_summary(filtered):
    """フィルタ結果の概要を表示"""
    print(f"\n=== フィルタ結果 ===")
    print(f"  合計: {len(filtered)}件")

    if not filtered:
        return

    # 勝敗集計
    wins = sum(1 for m in filtered if m.get("self", {}).get("win"))
    losses = len(filtered) - wins
    print(f"  勝利: {wins} / 敗北: {losses} ({wins / len(filtered) * 100:.1f}%)")

    # チャンピオン内訳
    champs = {}
    for m in filtered:
        cid = m.get("self", {}).get("championId", 0)
        if cid not in champs:
            champs[cid] = {"total": 0, "wins": 0}
        champs[cid]["total"] += 1
        if m.get("self", {}).get("win"):
            champs[cid]["wins"] += 1

    print(f"\n  チャンピオン内訳:")
    for cid, stats in sorted(champs.items(), key=lambda x: -x[1]["total"]):
        print(f"    ID {cid}: {stats['total']}回 ({stats['wins']}勝)")


def display_filtered_list(filtered, limit=10):
    """フィルタ結果をリスト表示"""
    if not filtered:
        print("\n  該当データがありません。")
        return

    show_count = min(limit, len(filtered))
    print(f"\n  (表示: {show_count}/{len(filtered)}件)")

    for i, m in enumerate(filtered[:show_count]):
        self_data = m.get("self", {})
        opp_data = m.get("opponent", {})
        match_data = m.get("match", {})

        champ_id = self_data.get("championId", 0)
        win = "勝利" if self_data.get("win") else "敗北"
        position = self_data.get("teamPosition", "?")
        opp_champ = opp_data.get("championId", "?")
        queue = match_data.get("queueId", "?")

        print(f"  [{i + 1}] {win} | {position} | チャンピオン:{champ_id} vs 対面:{opp_champ} | Queue:{queue}")

    if len(filtered) > limit:
        print(f"\n  ... 以下 {len(filtered) - limit}件あり")


def load_filtered_ids(output_path):
    """既存のfiltered.jsonからgameIdのセットを取得"""
    existing_ids = set()
    if not os.path.exists(output_path):
        return existing_ids
    
    try:
        existing = load_data(output_path)
        for m in existing:
            game_id = m.get("match", {}).get("gameId")
            if game_id:
                existing_ids.add(str(game_id))
    except Exception:
        pass
    
    return existing_ids


def generate_filename(filters, data_dir):
    """フィルタ条件からファイル名を生成"""
    parts = ["filtered"]
    
    if filters.get("champion_id"):
        parts.append(f"champ_{filters['champion_id']}")
    if filters.get("queue_id"):
        parts.append(f"queue_{filters['queue_id']}")
    if filters.get("position"):
        parts.append(f"pos_{filters['position']}")
    
    filename = "_".join(parts) + ".json"
    return os.path.join(data_dir, "data", filename)


def save_filtered(filtered, output_path):
    """フィルタ結果を保存（重複チェック付き）"""
    # 既存データを読み込み
    existing_ids = load_filtered_ids(output_path)
    
    if not existing_ids:
        # 既存データがない場合はそのまま保存
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(filtered, f, indent=2, ensure_ascii=False)
        print(f"\n  保存完了: {output_path} ({len(filtered)}件)")
        return
    
    # 既存データとマージ（重複ゲームIDは除外）
    merged_data = []
    duplicate_count = 0
    
    for m in filtered:
        game_id = m.get("match", {}).get("gameId")
        if str(game_id) in existing_ids:
            duplicate_count += 1
            continue
        merged_data.append(m)
    
    # 既存ファイルに追記
    existing = load_data(output_path)
    final_data = existing + merged_data
    
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n  保存完了: {output_path}")
    print(f"  既存: {len(existing)}件, 新規: {len(merged_data)}件, 重複: {duplicate_count}件")


def load_puuids(data_dir):
    """保存されたPUUID一覧を読み込む"""
    puuids_path = os.path.join(data_dir, "puuids.json")
    puuid_path = os.path.join(data_dir, "puuid.json")
    
    result = []
    
    # puuids.json を読み込む
    if os.path.exists(puuids_path):
        try:
            data = load_data(puuids_path)
            if isinstance(data, list):
                result.extend(data)
        except Exception:
            pass
    
    # puuid.json を読み込む（単一PUUID形式）
    if os.path.exists(puuid_path):
        try:
            data = load_data(puuid_path)
            if isinstance(data, dict):
                result.append(data)
            elif isinstance(data, list):
                result.extend(data)
        except Exception:
            pass
    
    return result


def interactive_filter(matchups, puuids_data):
    """対話式フィルタメニュー"""
    filters = {}

    queue_map = {"420": "ソロデュオ", "440": "フレックス", "430": "通常5v5", "400": "URF"}
    position_map = {"TOP": "上", "JUNGLE": "森", "MIDDLE": "中", "BOTTOM": "下", "UTILITY": "支"}

    print(f"\n{'=' * 50}")
    print(f"PUUID選択:")
    
    if not puuids_data:
        print(f"  保存されたPUUIDがありません。fetch_data.pyで取得してください。")
    else:
        for i, p in enumerate(puuids_data, 1):
            name = p.get("game_name", "")
            tag = p.get("tag_line", "")
            print(f"  [{i}] {name}/{tag}")
        print(f"  [0] 指定なし（全プレイヤー）")
        
        pchoice = input("\nPUUID選択番号: ").strip()
        if pchoice == "0":
            print("PUUIDフィルタなしで続行します。")
        else:
            try:
                idx = int(pchoice) - 1
                if 0 <= idx < len(puuids_data):
                    filters["puuid"] = puuids_data[idx]["puuid"]
                else:
                    print("無効な選択です。")
            except ValueError:
                print("無効な入力です。")

    while True:
        filtered = filter_matchups(matchups, filters)

        # 現在のフィルタ状態を表示
        print(f"\n{'=' * 50}")
        print(f"現在のフィルタ:")
        print(f"  PUUID: {filters.get('puuid', 'なし')[:10]}...")
        if filters.get("champion_id"):
            print(f"  チャンピオン: ID {filters['champion_id']}")
        if filters.get("queue_id"):
            print(f"  ゲームモード: {queue_map.get(str(filters['queue_id']), str(filters['queue_id']))}")
        if filters.get("position"):
            print(f"  ポジション: {filters['position']}")

        print(f"\n=== 結果: {len(filtered)}件 ===")
        display_summary(filtered)

        print(f"\n--- 操作 ---")
        print(f"  [1] チャンピオンでフィルタ")
        print(f"  [2] ゲームモードでフィルタ")
        print(f"  [3] ポジションでフィルタ")
        print(f"  [4] フィルタ一覧・解除")
        print(f"  [5] 詳細リスト表示")
        print(f"  [6] 結果を保存")
        print(f"  [0] 終了")

        choice = input("\n選択: ").strip()

        if choice == "1":
            champ_input = input("チャンピオン名/ID (空白で解除): ").strip()
            if champ_input:
                filters["champion_id"] = resolve_champion_input(champ_input)
            else:
                filters.pop("champion_id", None)

        elif choice == "2":
            print("ゲームモード選択:")
            print("  [1] ソロデュオ (420)")
            print("  [2] フレックス (440)")
            print("  [3] 通常5v5 (430)")
            print("  [4] URF (400)")
            print("  [0] 解除")
            q_input = input("選択: ").strip()
            q_map = {"1": 420, "2": 440, "3": 430, "4": 400}
            if q_input in q_map:
                filters["queue_id"] = q_map[q_input]
            elif q_input == "0":
                filters.pop("queue_id", None)

        elif choice == "3":
            print("ポジション選択:")
            print("  [1] TOP (上)")
            print("  [2] JUNGLE (森)")
            print("  [3] MIDDLE (中)")
            print("  [4] BOTTOM (下)")
            print("  [5] UTILITY (支)")
            print("  [0] 解除")
            p_input = input("選択: ").strip()
            p_map = {"1": "TOP", "2": "JUNGLE", "3": "MIDDLE", "4": "BOTTOM", "5": "UTILITY"}
            if p_input in p_map:
                filters["position"] = p_map[p_input]
            elif p_input == "0":
                filters.pop("position", None)

        elif choice == "4":
            print(f"\n  有効フィルタ:")
            if filters.get("champion_id"):
                print(f"    チャンピオン: ID {filters['champion_id']}")
            if filters.get("queue_id"):
                print(f"    ゲームモード: {queue_map.get(str(filters['queue_id']), str(filters['queue_id']))}")
            if filters.get("position"):
                print(f"    ポジション: {filters['position']}")
            if not any(filters.get(k) for k in ["champion_id", "queue_id", "position"]):
                print(f"    (フィルタなし)")
            input("\n  (続けるにはEnter)")

        elif choice == "5":
            display_filtered_list(filtered)
            input("\n  (続けるにはEnter)")

        elif choice == "6":
            output_path = generate_filename(filters, os.path.dirname(__file__))
            print(f"  ファイル: {output_path}")
            save_filtered(filtered, output_path)

        elif choice == "0":
            print("\n終了しました。")
            break


if __name__ == "__main__":
    data_dir = os.path.join(os.path.dirname(__file__), "data")

    puuids_data = load_puuids(data_dir)
    print(f"PUUID一覧: {len(puuids_data)}件\n")

    data_path = os.path.join(data_dir, "lane_matchups.json")
    if not os.path.exists(data_path):
        print(f"データファイルが見つかりません: {data_path}")
        exit()

    matchups = load_data(data_path)
    print(f"データ読み込み完了: {len(matchups)}件\n")

    interactive_filter(matchups, puuids_data)