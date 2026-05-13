import json
import os


def load_champions():
    path = os.path.join(os.path.dirname(__file__), "data", "champions.json")
    with open(path, "r", encoding="utf-8") as f:
        champs = json.load(f)
    return {c["id"]: c["name"] for c in champs}


def list_available_files(data_dir):
    """利用可能なフィルターファイルを一覧表示"""
    files = []
    if not os.path.exists(data_dir):
        return files
    for f in os.listdir(data_dir):
        if f.startswith("filtered") and f.endswith(".json"):
            files.append(f)
    return sorted(files)


def analyze_opponents(data_path=None):
    if not data_path:
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        available = list_available_files(data_dir)
        
        if not available:
            print("データファイルが見つかりません: data/filtered*.json")
            return
        
        print(f"\n利用可能なデータファイル ({len(available)}件):")
        for i, fname in enumerate(available, 1):
            fpath = os.path.join(data_dir, fname)
            size = os.path.getsize(fpath)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    count = len(json.load(f))
            except Exception:
                count = "?"
            print(f"  [{i}] {fname} ({count}件, {size / 1024:.1f}KB)")
        print(f"  [0] 終了")
        
        choice = input("\nファイル選択: ").strip()
        if choice == "0":
            return
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(available):
                data_path = os.path.join(data_dir, available[idx])
            else:
                print("無効な選択です。")
                return
        except ValueError:
            print("無効な入力です。")
            return

    if not os.path.exists(data_path):
        print(f"データファイルが見つかりません: {data_path}")
        return

    with open(data_path, "r", encoding="utf-8") as f:
        matchups = json.load(f)

    print(f"\nデータ: {os.path.basename(data_path)} ({len(matchups)}件)")

    champs = load_champions()
    opp_stats = {}

    for m in matchups:
        opp_id = m.get("opponent_id") or m.get("opponent", {}).get("championId")
        if not opp_id:
            continue

        win = m.get("win") or m.get("self", {}).get("win", False)

        if opp_id not in opp_stats:
            opp_stats[opp_id] = {"total": 0, "wins": 0, "losses": 0}

        opp_stats[opp_id]["total"] += 1
        if win:
            opp_stats[opp_id]["wins"] += 1
        else:
            opp_stats[opp_id]["losses"] += 1

    sorted_opps = sorted(opp_stats.items(), key=lambda x: x[1]["total"], reverse=True)

    print(f"\n{'チャンピオン':<18} | {'合計':>5} | {'勝利':>5} | {'敗北':>5} | {'勝率':>7}")
    print("-" * 58)
    for cid, stats in sorted_opps:
        name = champs.get(cid, f"Unknown({cid})")
        wr = stats["wins"] / stats["total"] * 100 if stats["total"] > 0 else 0
        print(f"{name:<24} | {stats['total']:>7} | {stats['wins']:>7} | {stats['losses']:>7} | {wr:>6.1f}%")


if __name__ == "__main__":
    analyze_opponents()