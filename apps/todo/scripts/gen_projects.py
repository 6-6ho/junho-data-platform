#!/usr/bin/env python3
"""todo 카테고리용 프로젝트 목록 생성.

분류 정책 (도메인+제품, 12개 기준):
- jdp(junho-data-platform)/apps 내부 마이크로서비스는 도메인으로 묶는다
  (trade-* + 크립토 피드류 → trade, realestate-monitor → realestate, ...).
  JDP_DOMAIN 에 없는 jdp 앱은 제외(노이즈 컷). 새 jdp 도메인은 여기 추가.
- /home/junho 직속 독립 제품은 유지하되, 일부는 짧은 이름으로(RENAME).
  메타/툴링(app-factory, claude-harness, junho-data-platform 자신)은 제외.
  → 매핑/제외에 없는 새 최상위 프로젝트는 그대로 자동 등장(auto-sync 유지).
- 항상 마지막에 '개인'.

출력: ~/.config/todo/projects.json (todo 컨테이너에 ro 마운트, 홈 미노출).
cron 으로 주기 실행 → 새 제품 자동 반영.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
JDP = HOME / "junho-data-platform"
OUT = HOME / ".config" / "todo" / "projects.json"

MARKERS = (".git", "Dockerfile", "package.json", "pyproject.toml")
COMPOSE_GLOB = "docker-compose*.yml"

# jdp/apps 마이크로서비스 → 도메인 카테고리. 없는 앱은 제외.
JDP_DOMAIN = {
    "trade-backend": "trade",
    "trade-frontend": "trade",
    "trade-ingest": "trade",
    "exchange-ingest": "trade",
    "onchain-ingest": "trade",
    "whale-monitor": "trade",
    "listing-monitor": "trade",
    "investment-agent": "trade",
    "realestate-monitor": "realestate",
    "rag-server": "rag",
    "infra-monitor": "infra",
}

# 최상위 프로젝트 표시 이름 단축
RENAME = {
    "kkum-oracle": "kkum",
    "seojin-master": "seojin",
}

# 최상위에서 제외 (메타/툴링/데이터 디렉터리)
TOP_EXCLUDE = {
    "app-factory", "claude-harness", "junho-data-platform",
    "rag-data", "rag-backups", "rag-staging", "bin", "development", "lotto-preview",
}


def is_project(d: Path) -> bool:
    if any((d / m).exists() for m in MARKERS):
        return True
    return any(d.glob(COMPOSE_GLOB))


def top_level_projects() -> list[str]:
    out = []
    for d in HOME.iterdir():
        if not d.is_dir() or d.name.startswith(".") or d.name in TOP_EXCLUDE:
            continue
        if is_project(d):
            out.append(RENAME.get(d.name, d.name))
    return out


def jdp_domains() -> list[str]:
    apps = JDP / "apps"
    if not apps.is_dir():
        return []
    out = []
    for d in apps.iterdir():
        if d.is_dir() and d.name in JDP_DOMAIN:
            out.append(JDP_DOMAIN[d.name])
    return out


def main() -> None:
    names = set(top_level_projects()) | set(jdp_domains())
    ordered = sorted(names)
    ordered.append("개인")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(ordered, ensure_ascii=False, indent=2))
    print(f"wrote {len(ordered)} categories -> {OUT}")


if __name__ == "__main__":
    main()
