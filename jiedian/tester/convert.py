#!/usr/bin/env python3
"""把 vless/trojan/vmess 分享链接转成 mihomo (clash) proxies, 供真实握手测速。
用法: convert.py links.txt out.yaml [limit]
测速: 启动 mihomo -f out.yaml 后, 用其 API /proxies/<name>/delay 逐个测。
"""
import base64, json, sys, urllib.parse, yaml

def parse_vless(link, name):
    u = urllib.parse.urlparse(link)
    q = dict(urllib.parse.parse_qsl(u.query))
    p = {"name": name, "type": "vless", "server": u.hostname, "port": u.port,
         "uuid": urllib.parse.unquote(u.username), "udp": True}
    sec = q.get("security", "")
    if sec == "tls" or q.get("tls") == "1":
        p["tls"] = True
    if sec == "reality":
        p["tls"] = True
        p["reality-opts"] = {"public-key": q.get("pbk", ""), "short-id": q.get("sid", "")}
    sni = q.get("sni") or q.get("peer")
    if sni: p["servername"] = sni
    p["client-fingerprint"] = q.get("fp", "chrome")
    if q.get("flow"): p["flow"] = q["flow"]
    net = q.get("type", "tcp")
    p["network"] = net
    if net == "ws":
        opts = {"path": urllib.parse.unquote(q.get("path", "/"))}
        host = q.get("host")
        if host: opts["headers"] = {"Host": host}
        p["ws-opts"] = opts
    elif net == "grpc":
        p["grpc-opts"] = {"grpc-service-name": q.get("serviceName", "")}
    return p

def parse_trojan(link, name):
    u = urllib.parse.urlparse(link)
    q = dict(urllib.parse.parse_qsl(u.query))
    p = {"name": name, "type": "trojan", "server": u.hostname, "port": u.port,
         "password": urllib.parse.unquote(u.username), "udp": True}
    sni = q.get("sni") or q.get("peer")
    if sni: p["sni"] = sni
    if q.get("allowInsecure") == "1" or q.get("insecure") == "1":
        p["skip-cert-verify"] = True
    net = q.get("type", "tcp")
    if net == "ws":
        opts = {"path": urllib.parse.unquote(q.get("path", "/"))}
        host = q.get("host")
        if host: opts["headers"] = {"Host": host}
        p["ws-opts"] = opts
    return p

def parse_vmess(link, name):
    payload = link[len("vmess://"):].split("#")[0].split("?")[0]
    j = json.loads(base64.b64decode(payload + "=" * (-len(payload) % 4)).decode("utf-8", "ignore"))
    p = {"name": name, "type": "vmess", "server": j.get("add"), "port": int(j.get("port", 443)),
         "uuid": j.get("id"), "alterId": int(j.get("aid", 0)), "cipher": "auto", "udp": True}
    if str(j.get("tls", "")).lower() in ("tls", "1", "true"):
        p["tls"] = True
        if j.get("sni"): p["servername"] = j["sni"]
    net = j.get("net", "tcp")
    p["network"] = net
    if net == "ws":
        opts = {"path": j.get("path", "/")}
        if j.get("host"): opts["headers"] = {"Host": j["host"]}
        p["ws-opts"] = opts
    return p

def main():
    links = [l.strip() for l in open(sys.argv[1]) if "://" in l]
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else len(links)
    proxies, mapping = [], {}
    for i, lk in enumerate(links[:limit * 2]):
        if len(proxies) >= limit: break
        frag = urllib.parse.unquote(lk.split("#", 1)[1]) if "#" in lk else ""
        name = f"n{i:04d}"
        try:
            if lk.startswith("vless://"): p = parse_vless(lk, name)
            elif lk.startswith("trojan://"): p = parse_trojan(lk, name)
            elif lk.startswith("vmess://"): p = parse_vmess(lk, name)
            else: continue
            if not p.get("server") or not p.get("port"): continue
            proxies.append(p); mapping[name] = {"link": lk, "label": frag}
        except Exception as e:
            continue
    cfg = {"mixed-port": 17990, "external-controller": "127.0.0.1:19090", "mode": "rule",
           "log-level": "warning", "proxies": proxies,
           "proxy-groups": [{"name": "TEST", "type": "select", "proxies": [p["name"] for p in proxies]}],
           "rules": ["MATCH,TEST"]}
    yaml.safe_dump(cfg, open(sys.argv[2], "w"), allow_unicode=True)
    json.dump(mapping, open(sys.argv[2] + ".map.json", "w"), ensure_ascii=False)
    print(f"converted {len(proxies)} proxies -> {sys.argv[2]}")

if __name__ == "__main__":
    main()
