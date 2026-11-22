"""Replay the AUDIT-167 player journey from the root of a production web build."""

import argparse
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading

if not __debug__ or os.environ.get("PYTHONOPTIMIZE") not in (None, "", "0"):
    raise SystemExit("Acceptance requires Python assertions. Set PYTHONOPTIMIZE=0 and run without -O.")

from PIL import Image
from playwright.sync_api import Page, sync_playwright

# Fixed initial dex heading and entry count rendered by both calibration builds.
HANDBOOK_PIXELS = "3360262c4ef3b034acbbe756d0e109e6137546386ad9faac7f568dcad99e5ae5"

# Observe the game's real save slots. All changes are made by player input.
READ_SLOT = """async slot => {
  const db = await new Promise((ok, fail) => {
    const open = indexedDB.open('shanhaijing-rpg');
    open.onupgradeneeded = () => open.transaction.abort();
    open.onsuccess = () => ok(open.result);
    open.onerror = () => fail(open.error);
  });
  try {
    const record = await new Promise((ok, fail) => {
      const query = db.transaction('saves', 'readonly').objectStore('saves').get(slot);
      query.onsuccess = () => ok(query.result);
      query.onerror = () => fail(query.error);
    });
    return record ? {ts: record.ts, player: record.player, ver: record.ver} : null;
  } finally {
    db.close();
  }
}"""


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


class Replay:
    def __init__(self, page: Page, output: Path):
        self.page = page
        self.canvas = page.locator("canvas")
        self.output = output
        self.results = {"cases": {}, "manual_saves": [], "screens": {}, "page_errors": []}
        page.on("pageerror", lambda error: self.results["page_errors"].append(str(error)))

    def capture(self, name: str):
        image = self.canvas.screenshot(path=self.output / f"{name}.png")
        self.results["screens"][name] = hashlib.sha256(image).hexdigest()

    def press(self, key: str, ms: int = 100):
        self.page.keyboard.down(key)
        self.page.wait_for_timeout(ms)
        self.page.keyboard.up(key)
        self.page.wait_for_timeout(160)

    def click(self, x: int, y: int):
        box = self.canvas.bounding_box()
        self.page.mouse.click(box["x"] + box["width"] * x / 240, box["y"] + box["height"] * y / 160)
        self.page.wait_for_timeout(250)

    def read(self, slot: str = "manual-1"):
        return self.page.evaluate(READ_SLOT, slot)

    def manual_save(self):
        previous = self.read() or {"ts": 0}
        for attempt in range(12):
            self.press("k")
            for _ in range(8):
                record = self.read()
                if record and record["ts"] > previous["ts"]:
                    self.results["manual_saves"].append(record)
                    return record
                self.page.wait_for_timeout(120)
            self.capture(f"save-wait-{len(self.results['manual_saves'])}-{attempt}")
            # Flee a naturally occurring encounter and allow the return animation.
            self.press("4")
            self.page.wait_for_timeout(850)
        raise AssertionError(f"K did not create a fresh manual save, last record {self.read()}")

    def approach_elder(self, record):
        for _ in range(16):
            dx, dy = 10 - record["player"]["x"], 8 - record["player"]["y"]
            if abs(dx) <= 1 and abs(dy) <= 1:
                return
            if abs(dx) > 1:
                self.press("ArrowRight" if dx > 0 else "ArrowLeft", min(550, int((abs(dx) - .4) * 190)))
            else:
                self.press("ArrowDown" if dy > 0 else "ArrowUp", min(550, int((abs(dy) - .4) * 190)))
            record = self.manual_save()
        raise AssertionError(f"elder remained out of reach, last record {record}")

    def diverge_autosave(self, saved):
        """Distinguish a manual reload from reopening the more recent auto slot."""
        self.press("m")
        for _ in range(8):
            self.press("ArrowLeft", 450)
            auto = self.read("auto")
            if auto and auto["ts"] > saved["ts"] and auto["player"] != saved["player"]:
                assert self.read() == saved, "automatic save changed the manual slot"
                self.results["later_autosave"] = auto
                return
            self.press("4")
            self.page.wait_for_timeout(850)
        raise AssertionError("a distinct later autosave was not observed")

    def run(self, url: str, handbook_pixels: str):
        cases = self.results["cases"]
        current = "ordinary-title"
        try:
            response = self.page.goto(url)
            assert response and response.status == 200
            self.canvas.wait_for(timeout=20_000)
            self.page.wait_for_timeout(1600)
            self.capture("title")
            self.click(120, 78)
            for _ in range(3):
                self.press("z")
            first = self.manual_save()["player"]
            assert first["mapId"] == "demo01"
            cases[current] = True

            current = "handbook-returns-control"
            self.capture("before-menu")
            self.press("x")
            self.press("q")
            self.capture("handbook")
            with Image.open(self.output / "handbook.png") as image:
                heading = image.convert("RGB").crop((120, 0, 600, 105))
                digest = hashlib.sha256(heading.tobytes()).hexdigest()
            self.results["handbook_pixels_sha256"] = digest
            assert digest == handbook_pixels, "dex heading/count differs from the reference rendering"
            self.press("Escape")
            self.capture("return")
            self.press("ArrowRight", 400)
            moved = self.manual_save()
            assert (moved["player"]["x"], moved["player"]["y"]) != (first["x"], first["y"])
            assert self.results["screens"]["handbook"] != self.results["screens"]["before-menu"]
            cases[current] = True

            current = "interact-and-save"
            self.approach_elder(moved)
            self.press("z")
            self.press("z")
            self.capture("elder-choice")
            self.click(52, 101)
            self.press("z")
            self.press("z")
            saved = self.manual_save()
            assert saved["player"]["flags"].get("elder_told") is True
            cases[current] = True

            current = "return-title-and-restore"
            self.diverge_autosave(saved)
            self.page.reload()
            self.canvas.wait_for()
            self.page.wait_for_timeout(1400)
            self.capture("second-title")
            self.click(120, 110)
            restored = self.manual_save()
            assert restored["player"] == saved["player"], "manual player state did not round-trip"
            self.results["original_player"] = saved["player"]
            self.results["restored_player"] = restored["player"]
            self.capture("loaded")
            assert not self.results["page_errors"], self.results["page_errors"]
            cases[current] = True
            self.results["passed"] = True
        except Exception as exc:
            cases[current] = False
            self.results.update(passed=False, failure=repr(exc))
        return self.results


def assess(bundle: Path, output: Path, seed: int, channel: str, handbook_pixels: str):
    if not (bundle / "index.html").is_file():
        raise ValueError(f"missing production index.html in {bundle}")
    output.mkdir(parents=True, exist_ok=False)
    handler = partial(QuietHandler, directory=str(bundle))
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    headless=True, channel=channel,
                    args=["--enable-unsafe-swiftshader", f"--js-flags=--random-seed={seed}"],
                )
                try:
                    context = browser.new_context(viewport={"width": 1280, "height": 720})
                    page = context.new_page()
                    context.new_cdp_session(page).send("Emulation.setFocusEmulationEnabled", {"enabled": True})
                    result = Replay(page, output).run(f"http://127.0.0.1:{server.server_port}/", handbook_pixels)
                    result.update(browser=browser.version, seed=seed)
                finally:
                    browser.close()
        finally:
            server.shutdown()
    result["files"] = {
        file.relative_to(bundle).as_posix(): hashlib.sha256(file.read_bytes()).hexdigest()
        for file in sorted(bundle.rglob("*")) if file.is_file()
    }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("output", type=Path, help="new directory for this invocation")
    parser.add_argument("--seed", type=int, default=102)
    parser.add_argument("--channel", default="msedge", help="installed Playwright Chromium channel")
    parser.add_argument("--handbook-pixels", default=HANDBOOK_PIXELS, help="verified digest of the original dex heading/count on this platform")
    args = parser.parse_args()
    verdict = assess(args.bundle.resolve(strict=True), args.output.resolve(), args.seed, args.channel, args.handbook_pixels)
    (args.output / "verdict.json").write_text(
        json.dumps(verdict, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    print("PASS" if verdict["passed"] else f"FAIL: {verdict['failure']}")
    raise SystemExit(0 if verdict["passed"] else 1)
