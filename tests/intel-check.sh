#!/bin/bash
# 準備の手順（SKILL.md の「2. 道具を入れて確かめる」）のコマンドを、書いてあるとおりに取り出して実行し、
# 続けて動画づくりの試験（tests/reel_check.py）をする。道具が入っていない Mac と同じ状態から始める。
# 使い方: bash tests/intel-check.sh [結果を置くフォルダ]
set -u
cd "$(dirname "$0")/.."
OUT="${1:-$PWD/tests/out}"
mkdir -p "$OUT"
export PYTHONUSERBASE="$OUT/pyuser"

/usr/bin/python3 - plugins/reel-tsukuri/skills/junbi/SKILL.md "$OUT" <<'EOF'
import re, sys
sec = open(sys.argv[1]).read().split("## 2.")[1].split("## 3.")[0]
blocks = re.findall(r"```bash\n(.*?)```", sec, re.S)
if len(blocks) != 2:
    sys.exit(f"SKILL.md の 2 にあるコマンドが2つでない（{len(blocks)}）")
for i, b in enumerate(blocks, 1):
    open(f"{sys.argv[2]}/step2-{i}.sh", "w").write(b)
EOF
[ $? -eq 0 ] || exit 1

echo "== 2 の1つ目（版・空き・CPU）"
bash "$OUT/step2-1.sh" || exit 1
echo "== 2 の2つ目（道具を入れて確かめる）"
s=$(date +%s)
bash "$OUT/step2-2.sh" || exit 1
echo "（$(( $(date +%s) - s ))秒）"
echo "== 動画づくり"
/usr/bin/python3 tests/reel_check.py "$OUT"
