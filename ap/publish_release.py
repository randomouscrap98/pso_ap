#!/usr/bin/env python3
"""Build and publish a GitHub release with notes from ap/CHANGELOG.md. Talks to GitHub's REST API directly.
Never edits the changelog.

  ap/publish_release.py           prerelease v<world_version>-pre.N (next N); notes = the "Unreleased" section
                                  (everything since the last real release). Keeps the newest KEEP_PRERELEASES
                                  prereleases, deleting older ones (release and tag)
  ap/publish_release.py --final   draft release v<world_version>; notes = the "<world_version>" section (Unreleased
                                  renamed and cleaned up beforehand); publish the draft on GitHub

Token: GITHUB_TOKEN env var, or ap/.github_token (gitignored). Use a fine-grained token for this repo only with
"Contents: read and write". The working tree must be clean except CHANGELOG.md, and HEAD pushed, so the release
matches its tag. Builds with ap/generate_release.sh (pass build env like WIN_PREFIX through); the GitHub repo comes
from ap/release.json and the file names from the stamp in the built apworld."""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANGELOG = os.path.join(ROOT, "ap", "CHANGELOG.md")
TOKEN_FILE = os.path.join(ROOT, "ap", ".github_token")
REPO = json.load(open(os.path.join(ROOT, "ap", "release.json")))["repo"]  # also read by generate_release.sh
RELEASE_DIR = os.path.join(ROOT, "release")
UNRELEASED = "Unreleased"
KEEP_PRERELEASES = 5


def fail(msg: str) -> None:
    sys.exit(f"publish_release: {msg}")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def read_token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token and os.path.isfile(TOKEN_FILE):
        token = open(TOKEN_FILE).read().strip()
    if not token:
        fail(f"no GitHub token: set GITHUB_TOKEN or put one in {TOKEN_FILE}")
    return token


def check_tree() -> str:
    """Clean (except the changelog) and pushed: returns HEAD's sha."""
    dirty = [line for line in git("status", "--porcelain").splitlines() if not line.endswith("ap/CHANGELOG.md")]
    if dirty:
        fail("uncommitted changes (only ap/CHANGELOG.md may be):\n" + "\n".join(dirty))
    head = git("rev-parse", "HEAD")
    if not git("branch", "-r", "--contains", head):
        fail("HEAD isn't pushed (no remote branch contains it); push first")
    return head


def changelog_section(title: str) -> str:
    """Text of the changelog's "## <title>" section (the heading may continue after a space, e.g. with a date)."""
    parts = re.split(r"^## (.+)$", open(CHANGELOG, encoding="utf-8").read(), flags=re.M)
    for i in range(1, len(parts), 2):
        if parts[i].strip() == title or parts[i].startswith(title + " "):
            return parts[i + 1].strip()
    return ""


# GitHub API

class GitHub:
    def __init__(self, repo: str, token: str) -> None:
        self.repo, self.token = repo, token

    def request(self, method: str, url: str, body: bytes | None = None, content_type: str = "application/json"):
        if not url.startswith("https://"):
            url = f"https://api.github.com/repos/{self.repo}{url}"
        req = urllib.request.Request(url, data=body, method=method, headers={
            "Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "Content-Type": content_type, "User-Agent": "pso_ap-publish"})
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = resp.read()
                return json.loads(data) if data else None
        except urllib.error.HTTPError as e:
            fail(f"{method} {url} -> {e.code}: {e.read().decode(errors='replace')}")

    def create_release(self, tag: str, sha: str, body: str, prerelease: bool, draft: bool) -> dict:
        return self.request("POST", "/releases", json.dumps({
            "tag_name": tag, "target_commitish": sha, "name": tag, "body": body,
            "prerelease": prerelease, "draft": draft}).encode())

    def upload(self, release: dict, path: str) -> None:
        name = os.path.basename(path)
        url = release["upload_url"].split("{")[0] + "?" + urllib.parse.urlencode({"name": name})
        print(f"Uploading {name} ({os.path.getsize(path) / 1e6:.1f} MB)")
        self.request("POST", url, open(path, "rb").read(), "application/octet-stream")

    def delete_release(self, release: dict) -> None:
        self.request("DELETE", f"/releases/{release['id']}")
        if not release["draft"]:  # a published release created its tag; a draft's tag only exists once published
            self.request("DELETE", f"/git/refs/tags/{release['tag_name']}")


def prune_prereleases(gh: "GitHub") -> None:
    """Delete all but the newest KEEP_PRERELEASES published prereleases made by this script (and their tags)."""
    releases = gh.request("GET", "/releases?per_page=100")
    pre = [r for r in releases if r["prerelease"] and not r["draft"] and re.fullmatch(r"v.+-pre\.\d+", r["tag_name"])]
    pre.sort(key=lambda r: r["created_at"], reverse=True)
    for r in pre[KEEP_PRERELEASES:]:
        print(f"Deleting old prerelease {r['tag_name']}")
        gh.delete_release(r)


def next_prerelease(gh: "GitHub", version: str) -> int:
    refs = gh.request("GET", f"/git/matching-refs/tags/v{version}-pre.")
    numbers = [int(m.group(1)) for r in refs if (m := re.fullmatch(rf"refs/tags/v{re.escape(version)}-pre\.(\d+)",
                                                                     r["ref"]))]
    return max(numbers, default=0) + 1


def read_stamp() -> dict:
    """The server_release.py stamp inside the built apworld."""
    with zipfile.ZipFile(os.path.join(RELEASE_DIR, "pso_bb.apworld")) as z:
        stamp: dict = {}
        exec(z.read("pso_bb/server_release.py").decode(), stamp)  # our own build output
    return stamp


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--final", action="store_true", help="draft a real release instead of a prerelease")
    final = parser.parse_args().final

    gh = GitHub(REPO, read_token())
    head = check_tree()
    version = json.load(open(os.path.join(ROOT, "ap", "apworld", "pso_bb", "archipelago.json")))["world_version"]
    if final:
        suffix, title = "", version
    else:
        suffix, title = f"pre.{next_prerelease(gh, version)}", UNRELEASED
    notes = changelog_section(title)
    if not notes:
        fail(f'nothing to publish: no "## {title}" section with text in {CHANGELOG}'
             + (f" (rename {UNRELEASED} to {version} first)" if final else ""))
    full_version = f"{version}-{suffix}" if suffix else version

    print(f"Building {full_version} from {head[:10]}")
    subprocess.run([os.path.join(ROOT, "ap", "generate_release.sh"), *([suffix] if suffix else [])], cwd=ROOT,
                   check=True)
    stamp = read_stamp()
    if stamp["VERSION"] != full_version:
        fail(f"built {stamp['VERSION']}, expected {full_version}")
    files = [os.path.join(RELEASE_DIR, name) for name, _, _ in stamp["FILES"].values()]
    files += [os.path.join(RELEASE_DIR, "pso_bb.apworld"), os.path.join(RELEASE_DIR, "psobb-ap.yml")]

    tag = f"v{full_version}"
    body = f"{notes}\n\nBuilt from {head}."
    release = gh.create_release(tag, head, body, prerelease=not final, draft=final)
    try:
        for path in files:
            gh.upload(release, path)
    except BaseException:
        print("Upload failed; removing the partial release")
        gh.delete_release(release)
        raise

    print(f"{'Draft' if final else 'Prerelease'} {tag}: {release['html_url']}")
    if not final:
        prune_prereleases(gh)


if __name__ == "__main__":
    main()
