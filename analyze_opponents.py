import json
import os


def load_champions():
    path = os.path.join(os.path.dirname(__file__), "data", "champions.json")
    with open(path, "r", encoding="utf-8") as f:
        champs = json.load(f)
    return {c["id"]: c["name"] for c in champs}


def load_analysis_input():
    """data/analysis_input.json から main.py が指定したファイルパスを読み取る"""
    input_path = os.path.join(os.path.dirname(__file__), "data", "analysis_input.json")
    if not os.path.exists(input_path):
        return None
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("source_file")


def list_available_files(data_dir):
    files = []
    if not os.path.exists(data_dir):
        return files
    for f in os.listdir(data_dir):
        if f.startswith("filtered") and f.endswith(".json"):
            files.append(f)
    return sorted(files)


def generate_output_filename(data_path):
    base = os.path.splitext(os.path.basename(data_path))[0]
    return os.path.join(os.path.dirname(__file__), "data", f"{base}_analysis.txt")


def save_analysis_json(data_path, sorted_opps):
    """分析結果をJSONとして保存"""
    json_path = os.path.join(os.path.dirname(__file__), "data", "analysis_output.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "source_file": data_path,
            "opponents": {cid: stats for cid, stats in sorted_opps},
        }, f, indent=2, ensure_ascii=False)
    print(f"\nJSON保存: {json_path}")


def analyze_opponents(data_path=None, mode=None):
    # data_path が指定されていない場合は analysis_input.json を確認
    if not data_path:
        input_path = load_analysis_input()
        if input_path:
            data_path = input_path

    # それでもデータパスがない場合は対話式選択
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

    if mode is None:
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

    lines = []
    lines.append("チャンピオン\t| 合計\t| 勝利\t| 敗北\t| 勝率")
    lines.append("-" * 40)
    for cid, stats in sorted_opps:
        name = champs.get(cid, f"Unknown({cid})")
        wr = stats["wins"] / stats["total"] * 100 if stats["total"] > 0 else 0
        # タブで列を揃える (目標列: 16, タブ幅: 8)
        name_len = len(name)
        remaining = 16 - name_len
        tabs_after_name = max(1, -(-remaining // 8))
        padded_name = name + "\t" * tabs_after_name
        lines.append(f"{padded_name}| {stats['total']}\t| {stats['wins']}\t| {stats['losses']}\t| {wr:>6.1f}%")

    if mode is None:
        print(f"\n--- 出力モード ---")
        print(f"  [1] コンソール出力のみ")
        print(f"  [2] テキスト保存")
        print(f"  [3] コンソール出力＋テキスト保存")
        print(f"  [4] テキスト保存のみ")
        print(f"  [5] 分析結果を保存")

        mode = input("選択: ").strip() or "1"

    if mode == "5":
        print(f"\n分析結果を保存します。")
        output_path = generate_output_filename(data_path)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"データ: {os.path.basename(data_path)}\n")
            f.write(f"件数: {len(matchups)}件\n\n")
            for line in lines:
                f.write(line + "\n")
        print(f"\nテキスト保存: {output_path}")
        save_analysis_json(data_path, sorted_opps)
    else:
        save_to_file = mode in ["2", "4"]
        print_to_console = mode in ["1", "3"]

        if print_to_console:
            print()
            for line in lines:
                print(line)

        if save_to_file:
            output_path = generate_output_filename(data_path)
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"データ: {os.path.basename(data_path)}\n")
                f.write(f"件数: {len(matchups)}件\n\n")
                for line in lines:
                    f.write(line + "\n")
            print(f"\nテキスト保存: {output_path}")
            save_analysis_json(data_path, sorted_opps)


if __name__ == "__main__":
    analyze_opponents()