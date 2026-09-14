#!/usr/bin/env python3
"""Read-only non-root Docker HTTP smoke; uses old fixture queries, never final-v2 questions."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def request(port, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    item = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(item, timeout=10) as response:
            return response.status, json.loads(response.read()) if path != "/" else response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def inside():
    assert os.geteuid() != 0, "runtime must be non-root"
    assert platform.python_version() == "3.12.14", "target Python runtime changed"
    root = Path("/app")
    artifact = root / "config/human-knowledge-retrieval-v4.json"
    # Mounted verifier writes only its temporary test artifact/logs to the declared tmpfs.
    with tempfile.TemporaryDirectory(prefix="pvr-v4-smoke-") as directory:
        temporary = Path(directory)
        invalid = temporary / "invalid-artifact.json"
        invalid.write_text("{}")
        outputs = {}
        queries = ["2022 Chevy Nomad Red #101", "Toyota Supra", "Chevy Nomad", "red toy boxed"]
        for index, (name, option) in enumerate((("default", None), ("v4", str(artifact)),
                ("missing", "/app/config/does-not-exist-v4.json"), ("malformed", str(invalid)),
                ("stale", "/tmp/stale-config/human-knowledge-retrieval-v4.json"))):
            if name == "stale":
                # Stale evidence means an invalid mandatory checksum, not merely relocating the artifact.
                # The source-derived /app evidence ROOT deliberately remains fixed after packaging fix.
                stale = Path(option)
                stale.parent.mkdir(exist_ok=True)
                value = json.loads(artifact.read_text())
                value["selection_evidence"]["sha256"] = "0" * 64
                stale.write_text(json.dumps(value))
            port = 8120 + index
            environment = dict(os.environ, PVR_UI_PATH="/app/ui")
            environment.pop("PVR_HUMAN_KNOWLEDGE_RETRIEVAL_ARTIFACT", None)
            environment.pop("PVR_HUMAN_KNOWLEDGE_IDENTITY_ARTIFACT", None)
            if option:
                environment["PVR_HUMAN_KNOWLEDGE_IDENTITY_ARTIFACT"] = option
            with (temporary / f"{name}.log").open("w") as log:
                process = subprocess.Popen([sys.executable, "-m", "uvicorn", "product_variant_resolver.api:app",
                    "--host", "127.0.0.1", "--port", str(port), "--workers", "1"],
                    cwd=root, env=environment, stdout=log, stderr=log)
                try:
                    for attempt in range(100):
                        try:
                            status, health = request(port, "/health")
                            break
                        except (OSError, urllib.error.URLError):
                            if process.poll() is not None:
                                raise RuntimeError(f"{name} server exited: {(temporary / f'{name}.log').read_text()}")
                            time.sleep(.1)
                    else:
                        raise RuntimeError(f"{name} HTTP readiness timed out")
                    expected = 200 if name in {"default", "v4"} else 503
                    assert status == expected, (name, status, health)
                    row = {"health_status": status, "health": health}
                    if expected == 200:
                        row["responses"] = []
                        for query in queries:
                            code, payload = request(port, "/resolve", {"title": query})
                            assert code == 200
                            row["responses"].append(payload)
                        ui_code, ui = request(port, "/")
                        assert ui_code == 200 and "<html" in ui.lower()
                        row["ui_status"] = ui_code
                        code, payload = request(port, "/resolve", {"title": "Chevy Nomad", "debug": True})
                        assert code == 200
                        row["debug"] = payload["debug"]
                    else:
                        code, payload = request(port, "/resolve", {"title": "Chevy Nomad"})
                        assert code == 503
                        row["resolve_status"] = code
                    outputs[name] = row
                finally:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
        assert outputs["default"]["responses"] == outputs["v4"]["responses"], "canonical outputs changed"
        assert outputs["default"]["health"]["dependencies"]["human_knowledge_index"]["version"] == "human-knowledge-hybrid-v2"
        assert outputs["v4"]["health"]["dependencies"]["human_knowledge_index"]["version"] == "human-knowledge-hybrid-v4"
        debug = outputs["v4"]["debug"]
        assert debug["human_knowledge_identity_work"]["posting_entries_visited"] > 0
        assert debug["human_knowledge_character_index"]["form_count"] == 284
        assert debug["human_knowledge_character_index"]["posting_entry_count"] == 8051
        assert debug["human_knowledge_retrieval_artifact_sha256"] == hashlib.sha256(artifact.read_bytes()).hexdigest()
        from product_variant_resolver.human_knowledge_identity_artifact import RUNTIME_SOURCES
        return {"verdict": "PASS", "python": platform.python_version(), "system": platform.system(),
            "machine": platform.machine(), "uid": os.geteuid(), "read_only_container": True,
            "http_transport": "loopback_uvicorn_one_worker_no_published_host_port",
            "fixture_queries": queries, "new_final_queries_executed": False,
            "outputs": outputs, "source_sha256": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                for name in RUNTIME_SOURCES}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inside", action="store_true")
    parser.add_argument("--docker-image")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.inside:
        print(json.dumps(inside(), sort_keys=True))
        return
    if not args.docker_image or not args.output:
        parser.error("use --inside or --docker-image IMAGE --output PATH")
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if not output.is_relative_to(root / "reports") or output.exists():
        parser.error("output must be a new report within this project")
    command = ["docker", "run", "--rm", "--read-only", "--tmpfs", "/tmp:size=32m,mode=1777",
        "--mount", f"type=bind,source={Path(__file__).resolve()},target=/tmp/verify-v4.py,readonly",
        args.docker_image, "python", "/tmp/verify-v4.py", "--inside"]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr + result.stdout)
    payload = json.loads(result.stdout)
    inspect = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", args.docker_image],
        capture_output=True, text=True, check=True)
    payload.update(schema_version="pvr-human-knowledge-v4-runtime-smoke-v1", image=args.docker_image,
        image_id=inspect.stdout.strip(), verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        packaging_sha256={name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in ("Dockerfile", ".dockerignore", "docker-compose.yml")})
    for name, checksum in payload["source_sha256"].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != checksum:
            raise ValueError("image contains stale runtime source: " + name)
    sys.path.insert(0, str(root / "src"))
    from product_variant_resolver.human_knowledge_identity_selection import publish_new
    publish_new(output, payload)
    print("Non-root/read-only Docker HTTP smoke PASS:", output)


if __name__ == "__main__":
    main()
