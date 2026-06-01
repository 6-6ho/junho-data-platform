#!/usr/bin/env python3
"""todo 카테고리용 프로젝트 목록 생성.

/home/junho 직속 프로젝트 디렉터리 + junho-data-platform/apps/* 하위 앱 이름을
스캔해 JSON 배열로 ~/.config/todo/projects.json 에 쓴다. 이 파일은 todo 컨테이너에
read-only 로 마운트되어 datalist 프리셋이 된다 (홈 전체 마운트 회피).

cron 으로 주기 실행 → 새 프로젝트가 자동으로 카테고리에 등장.
파일 내용만 읽으므로 디렉터리 이름 외엔 아무것도 노출하지 않는다.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
JDP = HOME / "junho-data-platform"
OUT = HOME / ".config" / "todo" / "projects.json"

# 프로젝트로 인정하는 마커 (하나라도 있으면 프로젝트)
MARKERS = (".git", "Dockerfile", "package.json", "pyproject.toml")
COMPOSE_GLOB = "docker-compose*.yml"

# 카테고리에서 빼고 싶은 이름 (도구/데이터 디렉터리 등)
EXCLUDE = {"rag-data", "rag-backups", "rag-staging", "bin", "development", "lotto-preview"}


def is_project(d: Path) -> bool:
    if any((d / m).exists() for m in MARKERS):
        return True
    return any(d.glob(COMPOSE_GLOB))


def top_level_projects() -> list[str]:
    out = []
    for d in HOME.iterdir():
        if not d.is_dir() or d.name.startswith(".") or d.name in EXCLUDE:
            continue
        if is_project(d):
            out.append(d.name)
    return out


def jdp_apps() -> list[str]:
    apps = JDP / "apps"
    if not apps.is_dir():
        return []
    return [d.name for d in apps.iterdir() if d.is_dir() and not d.name.startswith(".")]


def main() -> None:
    names = set(top_level_projects()) | set(jdp_apps())
    ordered = sorted(names)
    ordered.append("개인")  # 항상 마지막에 개인
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(ordered, ensure_ascii=False, indent=2))
    print(f"wrote {len(ordered)} categories -> {OUT}")


if __name__ == "__main__":
    main()
