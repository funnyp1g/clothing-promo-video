#!/usr/bin/env python3
"""Standalone adapter for the retained clothing-morph-v1 renderer."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
SKILL_ROOT = Path(__file__).resolve().parents[1]
FONTS = ("NotoSansSC.ttf", "SourceHanSerifCN-Regular.otf")
FONT_FILES = FONTS + ("OFL.txt", "SourceHanSerif-LICENSE.txt", "SOURCES.md")
ASPECTS = {"9:16", "16:9", "1:1", "4:5"}
TARGETS = {"preview": {"short_edge": 720, "fps": 30},
           "final": {"short_edge": 1080, "fps": 60}}


def write_json(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), "utf-8")
    temp.replace(path)


def runtime():
    try:
        import PIL
        import numpy
        import imageio_ffmpeg
        from PIL import ImageFont
    except ImportError as exc:
        raise ValueError("缺少运行依赖；使用当前 Python 安装 scripts/requirements.txt") from exc
    for name in FONTS:
        ImageFont.truetype(str(SKILL_ROOT / "assets/fonts" / name), 24)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ffmpeg, "-version"], check=True, capture_output=True, timeout=15)
    return {"python": sys.executable, "pillow": PIL.__version__,
            "numpy": numpy.__version__, "imageio_ffmpeg": imageio_ffmpeg.__version__,
            "ffmpeg": ffmpeg, "fonts": [str(SKILL_ROOT / "assets/fonts" / n) for n in FONTS]}


def copy_file(source, destination):
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)


def allowed_fields(value, allowed, label):
    if not isinstance(value, dict):
        raise ValueError(label + "必须为 JSON 对象")
    extra = set(value) - set(allowed)
    if extra:
        raise ValueError(label + "包含不支持的字段：" + ", ".join(sorted(extra)))


def prepare(spec_path, workspace, env):
    from PIL import Image
    request = json.loads(spec_path.read_text("utf-8"))
    allowed_fields(request, ("assets", "looks", "classification", "logo_asset_id",
                             "duration", "music", "quality", "aspect"), "输入规格")
    quality = request.get("quality", "preview")
    aspect = request.get("aspect", "9:16")
    if quality not in TARGETS or aspect not in ASPECTS:
        raise ValueError("quality 必须为 preview/final；aspect 必须为 9:16/16:9/1:1/4:5")
    if not isinstance(request.get("music", True), bool):
        raise ValueError("music 必须为 JSON 布尔值 true 或 false")
    if "duration" in request:
        duration = request["duration"]
        if isinstance(duration, bool) or not isinstance(duration, (float, int)) or not math.isfinite(duration):
            raise ValueError("duration 必须为有限数字")
    for field in ("assets", "looks", "classification"):
        if not isinstance(request.get(field), list) or not request[field]:
            raise ValueError(field + "必须为非空数组")
    for look in request["looks"]:
        allowed_fields(look, ("asset_id", "category", "crop", "crop_reason"), "款式")
    for item in request["classification"]:
        allowed_fields(item, ("asset_id", "role", "reason"), "素材分类")
    identities = set()
    originals = []
    for item in request["assets"]:
        allowed_fields(item, ("id", "path", "role"), "图片资产")
        identity = item.get("id")
        if not isinstance(identity, str) or not identity.strip() or identity in identities:
            raise ValueError("每张图片需要非空且唯一的字符串 id")
        identities.add(identity)
        role = item.get("role", "material")
        if role not in ("material", "brand", "reference"):
            raise ValueError("图片用途必须为 material、brand 或 reference")
        raw_path = item.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            raise ValueError("每张图片需要 path")
        path = Path(raw_path).expanduser()
        path = (path if path.is_absolute() else spec_path.parent / path).resolve()
        if not path.is_file():
            raise ValueError("找不到图片：" + str(path))
        with Image.open(path) as image:
            if image.format not in ("PNG", "JPEG", "WEBP") or image.width * image.height > 40_000_000:
                raise ValueError("图片须为 PNG/JPEG/WebP，且不超过4000万像素")
            image.verify()
        originals.append((item, role, path))
    if sum(role == "brand" for _, role, _ in originals) > 1:
        raise ValueError("此 Skill 每次支持一张品牌图片，请先选定片尾使用的图片")
    classifications = {item.get("asset_id"): item.get("role") for item in request["classification"]}
    for item, role, _ in originals:
        expected = {"brand": "logo", "reference": "reference"}.get(role)
        if expected and classifications.get(item["id"]) != expected:
            raise ValueError("品牌用途须分类为logo，参考用途须分类为reference")
    workspace.mkdir(parents=True, exist_ok=True)
    for folder in ("inputs", "src", "assets/fonts", "artifacts", "tmp"):
        (workspace / folder).mkdir(parents=True, exist_ok=True)
    # A completed video may only share its workspace with the identical input.
    digest = hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    for _, _, path in originals:
        digest.update(path.read_bytes())
    fingerprint = digest.hexdigest()
    receipt = workspace / "input-fingerprint.json"
    if (workspace / "artifacts/video.mp4").exists():
        if not receipt.is_file() or json.loads(receipt.read_text("utf-8"))["sha256"] != fingerprint:
            raise ValueError("输出目录已有不同规格的成片，请使用新目录保留原版本")
    assets = []
    portable = {**request, "assets": []}
    for index, (item, role, original) in enumerate(originals, 1):
        destination = workspace / "inputs" / ("image-%03d" % index + original.suffix.lower())
        copy_file(original, destination)
        assets.append({"id": item["id"], "kind": "image", "role": role, "original": str(destination)})
        portable["assets"].append({"id": item["id"], "path": "../inputs/" + destination.name, "role": role})
    for name in FONT_FILES:
        copy_file(SKILL_ROOT / "assets/fonts" / name, workspace / "assets/fonts" / name)
    for name in ("clothing_morph.py", "render_video.py", "requirements.txt"):
        copy_file(Path(__file__).parent / name, workspace / "src" / name)
    context = {"assets": assets, "aspect": aspect, "quality": quality,
               "target": TARGETS[quality], "fonts": str(workspace / "assets/fonts"), "ffmpeg": env["ffmpeg"]}
    spec = {key: request[key] for key in ("looks", "classification", "logo_asset_id", "duration", "music") if key in request}
    write_json(workspace / "context.json", context)
    write_json(workspace / "src/clothing-spec.json", spec)
    write_json(workspace / "src/request.json", portable)
    write_json(receipt, {"sha256": fingerprint})
    return context, spec


def verify_video(video, context, spec, manifest, workspace):
    import imageio_ffmpeg
    reader = imageio_ffmpeg.read_frames(str(video))
    try:
        metadata = next(reader)
    finally:
        reader.close()
    width, height = metadata["size"]
    rx, ry = map(int, context["aspect"].split(":"))
    edge = context["target"]["short_edge"]
    expected_size = (2 * round(edge * rx / min(rx, ry) / 2), 2 * round(edge * ry / min(rx, ry) / 2))
    fps = context["target"]["fps"]
    if (width, height) != expected_size or abs(metadata["fps"] - fps) > .01 or metadata["codec"] != "h264":
        raise ValueError("视频尺寸、帧率或编码与目标不一致")
    if abs(metadata["duration"] - manifest["duration"]) > max(.2, 2 / fps):
        raise ValueError("视频实际时长与规格不一致")
    command = [context["ffmpeg"], "-nostdin", "-hide_banner", "-v", "error", "-xerror",
               "-i", str(video), "-map", "0:v:0"]
    music = spec.get("music", True)
    if music:
        command += ["-map", "0:a:0"]
    command += ["-progress", "pipe:1", "-nostats", "-f", "null", "-"]
    decoded = subprocess.run(command, capture_output=True, text=True, timeout=max(60, manifest["duration"] * 3))
    (workspace / "tmp/decode.log").write_text(decoded.stderr, "utf-8")
    matches = re.findall(r"^frame=\s*(\d+)\s*$", decoded.stdout, re.MULTILINE)
    frames = int(matches[-1]) if matches else 0
    if decoded.returncode or frames != round(manifest["duration"] * fps) or "progress=end" not in decoded.stdout:
        raise ValueError("视频或所需音轨未通过完整解码，请查看 tmp/decode.log")
    return {"width": width, "height": height, "fps": metadata["fps"], "frames": frames,
            "duration": metadata["duration"], "codec": metadata["codec"],
            "full_decode": True, "audio_required": music, "audio_decode_verified": music,
            "video_sha256": hashlib.sha256(video.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description="从本次服装图片生成独立可复现的宣传视频")
    parser.add_argument("--check", action="store_true", help="检查依赖、字体和 FFmpeg")
    parser.add_argument("--spec", type=Path, help="输入 JSON 文件")
    parser.add_argument("--output", type=Path, help="输出目录；不同规格使用不同目录")
    parser.add_argument("--keyframes", action="store_true", help="仅生成关键帧和转场拼图")
    args = parser.parse_args()
    try:
        env = runtime()
        if args.check:
            print(json.dumps({"ok": True, **env}, ensure_ascii=False))
            return
        if not args.spec or not args.output:
            parser.error("需要 --spec 和 --output，或使用 --check")
        workspace = args.output.expanduser().resolve()
        context, spec = prepare(args.spec.expanduser().resolve(), workspace, env)
        command = [sys.executable, str(workspace / "src/clothing_morph.py"), "--workspace", str(workspace),
                   "--spec", "src/clothing-spec.json"]
        if args.keyframes:
            command.append("--keyframes")
        with (workspace / "tmp/renderer.log").open("wb") as log:
            subprocess.run(command, cwd=workspace, stdout=log, stderr=subprocess.STDOUT, check=True)
        manifest = json.loads((workspace / "tmp/manifest-draft.json").read_text("utf-8"))
        result = {"stage": "keyframes" if args.keyframes else "completed", "workspace": str(workspace),
                  "poster": str(workspace / "artifacts/poster.jpg"), "keyframes": str(workspace / "tmp/keyframes.jpg"),
                  "transitions": str(workspace / "tmp/transitions.jpg"), "duration": manifest["duration"],
                  "quality": context["quality"]}
        if not args.keyframes:
            video = workspace / "artifacts/video.mp4"
            verification = verify_video(video, context, spec, manifest, workspace)
            write_json(workspace / "artifacts/manifest.json", manifest)
            write_json(workspace / "artifacts/verification.json", verification)
            result.update(video=str(video), manifest=str(workspace / "artifacts/manifest.json"),
                          verification=str(workspace / "artifacts/verification.json"), **verification)
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"ok": False, "error": str(exc), "hint": "渲染失败时查看输出目录 tmp/renderer.log、tmp/encode.log、tmp/decode.log"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
