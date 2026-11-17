#!/usr/bin/env python3
"""用已启动的 mihomo API 对 candidates 逐个做真实 delay 测试, 两轮, 输出测通链接。
用法: python3 test.py candidates.yaml.map.json passed.txt
前置: mihomo -f candidates.yaml 已启动, 控制口 127.0.0.1:19090
"""
import json, sys, urllib.request, urllib.parse, concurrent.futures, time

API = "http://127.0.0.1:19090"
TEST_URL = "https://www.gstatic.com/generate_204"

def delay(name, timeout_ms=6000):
    q = urllib.parse.urlencode({"url": TEST_URL, "timeout": timeout_ms})
    try:
        with urllib.request.urlopen(f"{API}/proxies/{name}/delay?{q}", timeout=timeout_ms / 1000 + 3) as r:
            d = json.loads(r.read())
            return d.get("delay")
    except Exception:
        return None

def run(names, workers=24):
    out = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(delay, n): n for n in names}
        for f in concurrent.futures.as_completed(futs):
            d = f.result()
            if d:
                out[futs[f]] = d
    return out

def main():
    mapping = json.load(open(sys.argv[1]))
    names = list(mapping.keys())
    print(f"total candidates: {len(names)}", flush=True)
    passed = run(names)
    print(f"round1 passed: {len(passed)}", flush=True)
    rest = [n for n in names if n not in passed]
    time.sleep(5)
    passed2 = run(rest)
    passed.update(passed2)
    print(f"round2 extra passed: {len(passed2)}", flush=True)
    rows = sorted(passed.items(), key=lambda kv: kv[1])
    with open(sys.argv[2], "w") as f:
        for name, d in rows:
            f.write(mapping[name]["link"] + "\n")
    with open(sys.argv[2] + ".report", "w") as f:
        for name, d in rows:
            f.write(f"{d}ms\t{mapping[name]['label']}\t{mapping[name]['link']}\n")
    print(f"FINAL passed: {len(rows)}")
    for name, d in rows[:40]:
        print(f"{d}ms {mapping[name]['label']}")

if __name__ == "__main__":
    main()
