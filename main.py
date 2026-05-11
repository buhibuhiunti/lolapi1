import json
import os
import sys
from collections import defaultdict


def load_matchups(data_path: str) -> list[dict]:
    """レーン対戦データを読み込み"""
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_counter(matchups: list[dict], target_summoner: str = "") -> None:
    """時間帯別カウンター分析"""
    if target_summoner:
        matchups = [m for m in matchups if m["summoner"] == target_summoner]

    if not matchups:
        print("データがありません")
        return

    # 集計: チャンピオン × 対戦相手 × 時間帯 → 勝率
    data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {"w": 0, "g": 0})))

    for m in matchups:
        champ = m["champion"]
        opp = m["opponent"]
        dur = m["duration_min"]
        win = m["win"]

        # 時間帯区分
        time_range = time_label(dur)
        data[champ][opp][time_range]["w"] += int(win)
        data[champ][opp][time_range]["g"] += 1

    # 出力
    for champ, opponents in data.items():
        print(f"\n{'=' * 50}")
        print(f" チャンピオン: {champ}")
        print(f"{'=' * 50}")

        for opp, time_data in opponents.items():
            print(f"\n  vs {opp}")

            # 時間帯でソート
            order = ["0-10min", "10-15min", "15-20min", "20-25min", "25min+"]
            for tr in order:
                if tr in time_data:
                    d = time_data[tr]
                    rate = (d["w"] / d["g"]) * 100
                    bar = "x" * int(rate / 5) + "-" * (20 - int(rate / 5))
                    print(f"    {tr:<10} {rate:>5.0f}% ({d['w']}/{d['g']}) [{bar}]")


def time_label(minutes: float) -> str:
    """試合時間を区分に分類"""
    if minutes < 10:
        return "0-10min"
    elif minutes < 15:
        return "10-15min"
    elif minutes < 20:
        return "15-20min"
    elif minutes < 25:
        return "20-25min"
    else:
        return "25min+"


def find_optimal_time(matchups: list[dict], target_summoner: str = "") -> None:
    """最良の試合時間を特定"""
    if target_summoner:
        matchups = [m for m in matchups if m["summoner"] == target_summoner]

    if not matchups:
        return

    # チャンピオン × 時間帯 → 勝率
    data = defaultdict(lambda: {"w": 0, "g": 0})

    for m in matchups:
        champ = m["champion"]
        tr = time_label(m["duration_min"])
        data[(champ, tr)]["w"] += int(m["win"])
        data[(champ, tr)]["g"] += 1

    # チャンピオンごとの最良時間帯
    champs = defaultdict(dict)
    for (champ, tr), d in data.items():
        champs[champ][tr] = d

    print("\n{'=' * 50}")
    print(" 最良の試合時間")
    print(f"{'=' * 50}")

    for champ, time_data in champs.items():
        best = max(time_data.items(), key=lambda x: x[1]["w"] / x[1]["g"] if x[1]["g"] > 0 else 0)
        worst = min(time_data.items(), key=lambda x: x[1]["w"] / x[1]["g"] if x[1]["g"] > 0 else 100)

        print(f"\n  {champ}")
        print(f"    最良: {best[0]} ({best[1]['w']}/{best[1]['g']} = {best[1]['w']/best[1]['g']*100:.0f}%)")
        print(f"    最悪: {worst[0]} ({worst[1]['w']}/{worst[1]['g']} = {worst[1]['w']/worst[1]['g']*100:.0f}%)")


if __name__ == "__main__":
    data_path = os.path.join(os.path.dirname(__file__), "data", "lane_matchups.json")

    if len(sys.argv) > 1:
        data_path = sys.argv[1]

    if not os.path.exists(data_path):
        print(f"ファイルが見つかりません: {data_path}")
        sys.exit(1)

    matchups = load_matchups(data_path)
    print(f"読み込み: {len(matchups)}レーン対戦 ({data_path})\n")

    # 特定プレイヤーをフィルタ
    target = sys.argv[2] if len(sys.argv) > 2 else ""

    analyze_counter(matchups, target)
    find_optimal_time(matchups, target)
