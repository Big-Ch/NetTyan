"""Install the verified Simple Voice Chat release and synthetic input in Kadr's profile."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

import requests

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / ".minecraft-course"
DATA = ROOT / "data"
VERSION = "fabric-1.21.11-2.6.27"


def setup():
    versions = requests.get(
        "https://api.modrinth.com/v2/project/simple-voice-chat/version",
        params={"loaders": '["fabric"]', "game_versions": '["1.21.11"]'},
        timeout=20,
    )
    versions.raise_for_status()
    release = next(item for item in versions.json() if item["version_number"] == VERSION)
    artifact = next(item for item in release["files"] if item["primary"])
    voicechat = GAME / "mods" / artifact["filename"]
    if not voicechat.exists():
        download = requests.get(artifact["url"], timeout=30)
        download.raise_for_status()
        if hashlib.sha512(download.content).hexdigest() != artifact["hashes"]["sha512"]:
            raise RuntimeError("Voice mod checksum mismatch")
        voicechat.write_bytes(download.content)
    if hashlib.sha512(voicechat.read_bytes()).hexdigest() != artifact["hashes"]["sha512"]:
        raise RuntimeError("Voice mod checksum mismatch")

    compiler = ROOT / "downloads/ecj-3.42.0.jar"
    if not compiler.exists():
        subprocess.run([os.sys.executable, str(ROOT / "tools/build_bootstrap.py")], check=True)
    mixin = next((GAME / "libraries/net/fabricmc/sponge-mixin").rglob("sponge-mixin-*.jar"))
    java = json.loads((DATA / "minecraft-install.json").read_text(encoding="utf-8"))["java"]
    classes = DATA / "voice-classes"
    sources = ROOT / "mods/kadr-bootstrap/src"
    subprocess.run([
        java, "-jar", str(compiler), "-21", "-proc:none",
        "-cp", os.pathsep.join(map(str, (voicechat, mixin))), "-d", str(classes),
        str(sources / "KadrSyntheticMicrophone.java"), str(sources / "KadrMicrophoneMixin.java"),
    ], check=True)
    target = GAME / "mods/kadr-voice-1.0.jar"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("fabric.mod.json", json.dumps({
            "schemaVersion": 1, "id": "kadr_voice", "version": "1.0", "environment": "client",
            "depends": {"voicechat": VERSION.removeprefix("fabric-")}, "mixins": ["kadr-voice.mixins.json"],
        }))
        archive.writestr("kadr-voice.mixins.json", json.dumps({
            "required": True, "package": "kadr.voice.mixin", "compatibilityLevel": "JAVA_21",
            "client": ["KadrMicrophoneMixin"], "injectors": {"defaultRequire": 1},
        }))
        for name in ("KadrSyntheticMicrophone.class", "mixin/KadrMicrophoneMixin.class"):
            archive.write(classes / "kadr/voice" / name, "kadr/voice/" + name)

    config = GAME / "config/voicechat/voicechat-client.properties"
    config.parent.mkdir(parents=True, exist_ok=True)
    updates = {"onboarding_finished": "true", "microphone_activation_type": "VOICE",
               "voice_activity_detection": "false", "voice_activation_threshold": "-48.0",
               "muted": "false", "disabled": "false"}
    old = config.read_text(encoding="utf-8").splitlines() if config.exists() else []
    if not old:
        old = ["config_version=1"]
    retained = [line for line in old if line.split("=", 1)[0].strip() not in updates]
    config.write_text("\n".join(retained + [f"{key}={value}" for key, value in updates.items()]) + "\n", encoding="utf-8")
    (DATA / "svc-install.json").write_text(json.dumps({
        "file": voicechat.name, "url": artifact["url"], "sha512": artifact["hashes"]["sha512"],
        "version": VERSION, "adapter": target.name,
    }, indent=2), encoding="utf-8")
    print("Installed", voicechat.name, "and", target.name)


if __name__ == "__main__":
    setup()
