"""Call the existing Detail Lab Claude routine after a successful main check.

Only GitHub Actions uses this script. The API credential belongs in the repository
secret CLAUDE_ROUTINE_FIRE_TOKEN; never write it into this file or the run logs.
"""

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPOSITORY = "51552462/detail-lab-site"
ROUTINE_ID = "trig_015KYJkVs92uyJCZ85Q1gtU2"
FIRE_URL = f"https://api.anthropic.com/v1/claude_code/routines/{ROUTINE_ID}/fire"


def request_json(url, headers, data=None):
    request = Request(url, headers=headers, data=data, method="POST" if data else "GET")
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def decide(sha, github_token, get_json=request_json):
    """Return a reason if this commit must not start another Claude session."""
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    base = f"https://api.github.com/repos/{REPOSITORY}"
    branch = get_json(f"{base}/branches/main", headers)
    if branch["commit"]["sha"] != sha:
        return "새 main 커밋이 있어 이전 검사 결과를 건너뜀"

    pulls = get_json(f"{base}/commits/{sha}/pulls?per_page=100", headers)
    if not isinstance(pulls, list):
        raise ValueError("커밋에 연결된 PR 목록 형식이 올바르지 않음")
    if any(
        pull.get("merged_at")
        and pull.get("merge_commit_sha") == sha
        and pull.get("head", {}).get("ref", "").startswith("claude/")
        for pull in pulls
    ):
        return "Claude가 병합한 PR이므로 재호출을 건너뜀"
    return None


def summary(message):
    print(message)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as output:
            output.write(message + "\n")


def main():
    sha = os.environ["SOURCE_SHA"]
    github_token = os.environ["GITHUB_TOKEN"]
    claude_token = os.environ.get("CLAUDE_ROUTINE_FIRE_TOKEN", "")
    reason = decide(sha, github_token)
    if reason:
        summary(reason)
        return 0
    if not claude_token:
        summary("Claude 즉시 실행 미연결: 저장소 secret CLAUDE_ROUTINE_FIRE_TOKEN이 없습니다.")
        return 0

    payload = json.dumps({"text": (
        f"GitHub main {sha}의 사이트 검사가 성공했습니다. "
        "저장된 디테일랩 검수 지침에 따라 최신 main과 인계 파일을 읽고 "
        "네 상품의 실제 고객 흐름을 검수·수정하세요."
    )}).encode("utf-8")
    result = request_json(FIRE_URL, {
        "Authorization": f"Bearer {claude_token}",
        "anthropic-beta": "experimental-cc-routine-2026-04-01",
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }, payload)
    session_url = result.get("claude_code_session_url", "")
    if not (
        session_url.startswith("https://claude.ai/code/session_")
        or session_url.startswith("https://claude.ai/code/session/")
    ):
        raise ValueError(
            "Claude 응답에서 실행 세션 URL을 확인하지 못함 "
            f"(응답 필드: {', '.join(sorted(result))})"
        )
    summary(f"Claude 후속 검수 시작: {session_url} (대상 main {sha})")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except HTTPError as error:
        print(f"GitHub 또는 Claude API HTTP 오류: {error.code}", file=sys.stderr)
        sys.exit(1)
    except (URLError, ValueError, KeyError) as error:
        print(f"후속 검수 호출 실패: {error}", file=sys.stderr)
        sys.exit(1)
