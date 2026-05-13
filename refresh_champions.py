import json
import urllib.request

url = "https://ddragon.leagueoflegends.com/cdn/15.10.1/data/en_US/champion.json"
req = urllib.request.Request(url)
req.add_header("User-Agent", "Mozilla/5.0")
req.add_header("Accept", "application/json")

with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read())

champs = data.get("data", {})
champ_list = []
for champ in champs.values():
    champ_list.append({
        "id": int(champ["key"]),
        "name": champ["name"],
    })

champ_list.sort(key=lambda x: x["id"])

with open("data/champions.json", "w", encoding="utf-8") as f:
    json.dump(champ_list, f, indent=2, ensure_ascii=False)

# Verify
print(f"再取得完了: {len(champ_list)}チャンピオン")
print(f"Vayne ID: {next(c['id'] for c in champ_list if c['name'] == 'Vayne')}")
print(f"Renekton ID: {next(c['id'] for c in champ_list if c['name'] == 'Renekton')}")