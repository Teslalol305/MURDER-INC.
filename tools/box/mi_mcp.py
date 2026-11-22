#!/usr/bin/env python3
"""Client for the Unreal Editor's built-in MCP server, used by the box scripts.

The server (plugin ModelContextProtocol, default http://127.0.0.1:8000/mcp) offers four tools: list_toolsets,
describe_toolsets, describe_tools and call_tool. Every editor tool is reached through call_tool.

  mi_mcp.py ping                               exit code 0 when the server answers
  mi_mcp.py toolsets [text]                    toolset names, optionally only those containing text
  mi_mcp.py describe <Toolset> [Tool]          tools of a toolset, one line each; with Tool: its input schema
  mi_mcp.py tool <Toolset.Tool> ['<json>']     call a tool and print its result as JSON
  mi_mcp.py py <file.py | -> [max_chars]       run Python inside the editor, print the value of its last expression
  mi_mcp.py level                              path of the level that is open in the editor
  mi_mcp.py shot <out.png> [options]           capture a picture (see shot.sh for the options)

Only the standard library is needed. Pillow is used for the image statistics when it is installed.
"""
import base64
import json
import os
import struct
import sys
import time
import urllib.request
import zlib

URL = os.environ.get("MI_MCP_URL", "http://127.0.0.1:8000/mcp")
PYTHON_TOOLSET = "editor_toolset.toolsets.python_scripting.PythonScriptingTools"
CAPTURE_TOOLSET = "SceneCaptureToolset.SceneCaptureToolset"


class McpError(Exception):
    pass


class Mcp:
    def __init__(self, url=URL, timeout=45):
        self.url, self.timeout, self.sid, self.next_id = url, timeout, None, 1
        self.rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                                "clientInfo": {"name": "mi-box", "version": "1"}})
        try:
            self.post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        except Exception:
            pass

    def post(self, payload):
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.sid:
            headers["Mcp-Session-Id"] = self.sid
        request = urllib.request.Request(self.url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            body = response.read().decode("utf-8", "replace")
            self.sid = response.headers.get("Mcp-Session-Id") or self.sid
            content_type = response.headers.get("Content-Type", "")
        if "text/event-stream" in content_type:
            messages = [json.loads(line[5:].strip()) for line in body.splitlines()
                        if line.startswith("data:") and line[5:].strip()]
            for message in messages:
                if "id" in message and ("result" in message or "error" in message):
                    return message
            return messages[-1] if messages else None
        return json.loads(body) if body.strip() else None

    def rpc(self, method, params=None):
        payload = {"jsonrpc": "2.0", "id": self.next_id, "method": method}
        self.next_id += 1
        if params is not None:
            payload["params"] = params
        answer = self.post(payload)
        if not answer:
            raise McpError("empty answer to " + method)
        if "error" in answer:
            raise McpError(json.dumps(answer["error"])[:2000])
        return answer.get("result", {})

    def meta(self, name, arguments):
        """Call one of the four top-level tools. Returns (value, content blocks)."""
        result = self.rpc("tools/call", {"name": name, "arguments": arguments})
        content = result.get("content", [])
        text = "\n".join(block.get("text", "") for block in content if block.get("type") == "text")
        if result.get("isError"):
            raise McpError(text[:4000] or "tool error without a message")
        value = result.get("structuredContent")
        if value is None:
            try:
                value = json.loads(text)
            except ValueError:
                value = text
        if isinstance(value, dict) and set(value) == {"returnValue"}:
            value = value["returnValue"]
        return value, content

    def tool(self, full_name, arguments=None):
        """Call Toolset.Tool. The toolset name may itself contain dots: the tool is the last part."""
        toolset, _, tool = full_name.rpartition(".")
        if not toolset:
            raise McpError("give the tool as Toolset.Tool, got " + full_name)
        return self.meta("call_tool", {"toolset_name": toolset, "tool_name": tool, "arguments": arguments or {}})

    def python(self, source):
        value, _ = self.tool(PYTHON_TOOLSET + ".execute_python", {"script": {"content": source, "language": "Python"}})
        return value


# ---------------------------------------------------------------------------------------------- image statistics

def png_stats_pure(data):
    """Width, height, mean brightness (0-255) and share of near-black pixels of an 8-bit PNG, without Pillow."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG file")
    position, idat, header = 8, [], None
    while position + 8 <= len(data):
        length, kind = struct.unpack(">I4s", data[position:position + 8])
        chunk = data[position + 8:position + 8 + length]
        position += 12 + length
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", chunk)
        elif kind == b"IDAT":
            idat.append(chunk)
        elif kind == b"IEND":
            break
    width, height, depth, colour, _, _, interlace = header
    channels = {0: 1, 2: 3, 4: 2, 6: 4}.get(colour)
    if depth != 8 or channels is None or interlace:
        raise ValueError("unsupported PNG layout (need 8-bit, not interlaced, not palette)")
    raw = zlib.decompress(b"".join(idat))
    stride = width * channels
    previous = bytearray(stride)
    total = dark = count = 0
    step = max(1, width // 480)          # sample at most about 480 pixels per row
    for y in range(height):
        start = y * (stride + 1)
        kind = raw[start]
        row = bytearray(raw[start + 1:start + 1 + stride])
        if kind == 1:
            for i in range(channels, stride):
                row[i] = (row[i] + row[i - channels]) & 255
        elif kind == 2:
            row = bytearray((a + b) & 255 for a, b in zip(row, previous))
        elif kind == 3:
            for i in range(stride):
                left = row[i - channels] if i >= channels else 0
                row[i] = (row[i] + ((left + previous[i]) >> 1)) & 255
        elif kind == 4:
            for i in range(stride):
                a = row[i - channels] if i >= channels else 0
                b = previous[i]
                c = previous[i - channels] if i >= channels else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                row[i] = (row[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        previous = row
        if y % step:
            continue
        for x in range(0, width, step):
            i = x * channels
            if channels >= 3:
                luma = (row[i] * 299 + row[i + 1] * 587 + row[i + 2] * 114) // 1000
            else:
                luma = row[i]
            total += luma
            dark += luma < 8
            count += 1
    return width, height, total / max(count, 1), dark / max(count, 1)


def image_stats(data):
    try:
        import io
        from PIL import Image, ImageStat
    except ImportError:
        return png_stats_pure(data)
    image = Image.open(io.BytesIO(data))
    grey = image.convert("RGB").convert("L")
    histogram = grey.histogram()
    return image.size[0], image.size[1], ImageStat.Stat(grey).mean[0], sum(histogram[:8]) / max(sum(histogram), 1)


# ------------------------------------------------------------------------------------------------------- capture

def find_image(content):
    for block in content:
        if block.get("type") == "image" and block.get("data"):
            return base64.b64decode(block["data"])
    return None


def run_console(mcp, command):
    mcp.python(
        "import unreal\n"
        "subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)\n"
        "world = subsystem.get_game_world() or subsystem.get_editor_world()\n"
        "unreal.SystemLibrary.execute_console_command(world, %r)\n" % command)


def pick_world(mcp, view):
    """The play-in-editor (or game) world when there is one and the caller did not ask for the editor world."""
    worlds, _ = mcp.tool(CAPTURE_TOOLSET + ".ListWorlds", {})
    worlds = [w for w in (worlds or []) if w.get("bCanCapture", True)]
    game = [w for w in worlds if w.get("worldType") in ("PIE", "Game")]
    editor = [w for w in worlds if w.get("worldType") == "Editor"]
    if view == "game" and not game:
        raise McpError("no game world: start play-in-editor first (EditorToolset.EditorAppToolset.StartPIE)")
    chosen = game[0] if game and view != "editor" else (editor[0] if editor else None)
    if chosen is None:
        raise McpError("no world to capture: " + json.dumps(worlds)[:300])
    return chosen


def shot_frames(mcp, out_path, numbers, fov, width, height, frames, game):
    """A converged picture: Content/Python/mi_shot.py renders the view once per editor tick for `frames` frames."""
    done = out_path + ".done"
    mcp.python(
        "import importlib, sys, unreal\n"
        "path = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + 'Python'\n"
        "sys.path.insert(0, path) if path not in sys.path else None\n"
        "import mi_shot\n"
        "importlib.reload(mi_shot)\n"
        "mi_shot.start(%r, %r, %r, fov=%r, width=%d, height=%d, frames=%d, game=%r)\n"
        % (out_path, tuple(numbers[:3]), tuple(numbers[3:6]), fov, width, height, frames, game))
    deadline = time.time() + 38
    while not os.path.exists(done):
        if time.time() > deadline:
            raise McpError("no picture after 38 s (%d frames): the editor is not ticking, or use fewer frames" % frames)
        time.sleep(0.4)
    with open(done, encoding="utf-8") as handle:
        text = handle.read()
    os.remove(done)
    if text != "OK":
        raise McpError("mi_shot: " + text)
    with open(out_path, "rb") as handle:
        return handle.read()


def shot(mcp, out_path, options):
    """Save a capture to out_path and return a one-line report."""
    width, height = (int(v) for v in options.get("size", "1920x1080").lower().split("x"))
    mode = options.get("mode", "Lit")
    view = options.get("view", "auto")
    for command in options.get("exec", []):
        run_console(mcp, command)
    if options.get("wait"):
        time.sleep(float(options["wait"]))
    capture_options = {"width": width, "height": height, "screenPercentage": 1, "visualizationSubMode": ""}
    world = pick_world(mcp, view)
    is_game = world.get("worldType") in ("PIE", "Game")
    via = None
    content = []
    data = None
    frames = int(options.get("frames", 24))
    if "cam" in options and frames > 0:
        numbers = [float(v) for v in options["cam"].split(",")]
        numbers += [0.0] * (6 - len(numbers))
        data = shot_frames(mcp, out_path, numbers, float(options.get("fov", 90)), width, height, frames, view != "editor")
        via = "mi_shot %d frames, %s world" % (frames, world.get("worldType"))
    elif "cam" in options:
        numbers = [float(v) for v in options["cam"].split(",")]
        numbers += [0.0] * (6 - len(numbers))
        camera = {"location": {"x": numbers[0], "y": numbers[1], "z": numbers[2]},
                  "rotation": {"pitch": numbers[3], "yaw": numbers[4], "roll": numbers[5]},
                  "projectionMode": "Perspective", "fOV": float(options.get("fov", 90)), "orthoWidth": 512}
        _, content = mcp.tool(CAPTURE_TOOLSET + ".Capture",
                              {"world": world["world"], "camera": camera, "mode": mode, "options": capture_options})
        via = "Capture(cam) %s world" % world.get("worldType")
    elif is_game:
        # The player's own view, rendered offscreen at the requested size; if that fails, the viewport as drawn.
        try:
            views, _ = mcp.tool(CAPTURE_TOOLSET + ".ListViews", {"world": world["world"]})
            player = [v for v in (views or []) if any(k.lower().startswith("bisplayer") and v[k] for k in v)] or views
            camera = player[0].get("camera", player[0])
            _, content = mcp.tool(CAPTURE_TOOLSET + ".Capture",
                                  {"world": world["world"], "camera": camera, "mode": mode, "options": capture_options})
            via = "Capture(player view) %s world" % world.get("worldType")
        except Exception as error:      # noqa: BLE001 - fall back to the plain viewport capture
            sys.stderr.write("player-view capture failed (%s), using CaptureGameViewport\n" % str(error)[:300])
            _, content = mcp.tool(CAPTURE_TOOLSET + ".CaptureGameViewport",
                                  {"world": world["world"], "maxResolution": max(width, height)})
            via = "CaptureGameViewport"
    else:
        _, content = mcp.tool(CAPTURE_TOOLSET + ".CaptureActiveEditorView", {"mode": mode, "options": capture_options})
        via = "CaptureActiveEditorView"
    data = data or find_image(content)
    if not data:
        raise McpError("the capture returned no image: " + json.dumps(content)[:400])
    with open(out_path, "wb") as handle:
        handle.write(data)
    w, h, mean, dark = image_stats(data)
    verdict = "BLACK" if mean < 2.0 or dark > 0.995 else "OK"
    return "SHOT %s %s %dx%d %d bytes mean=%.1f/255 near-black=%.1f%% via %s" % (
        verdict, out_path, w, h, len(data), mean, dark * 100.0, via), verdict


# ---------------------------------------------------------------------------------------------------------- main

def text_of(value, limit):
    text = value if isinstance(value, str) else json.dumps(value, indent=1, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + "\n... (%d more characters)" % (len(text) - limit)


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 2
    command = argv[1]
    try:
        mcp = Mcp(timeout=3 if command == "ping" else 45)
        if command == "ping":
            print("MCP ok")
        elif command == "toolsets":
            text, _ = mcp.meta("list_toolsets", {})
            wanted = argv[2].lower() if len(argv) > 2 else ""
            names = [line[2:].split(":", 1)[0] for line in str(text).splitlines() if line.startswith("- ")]
            print("\n".join(name for name in names if wanted in name.lower()))
        elif command == "describe":
            if len(argv) > 3:
                value, _ = mcp.meta("describe_tools", {"tool_names": [argv[2] + "." + argv[3]]})
                print(text_of(value, 12000))
            else:
                value, _ = mcp.meta("describe_toolsets", {"toolset_names": [argv[2]]})
                for name, toolset in (value.get("toolsets") or {}).items():
                    print("%s: %s" % (name, " ".join(toolset.get("description", "").split())[:300]))
                    for tool in toolset.get("tools", []):
                        print("  %s: %s" % (tool["name"].rsplit(".", 1)[-1], " ".join(tool.get("description", "").split())[:200]))
                if value.get("errors"):
                    print("errors: " + json.dumps(value["errors"]))
        elif command == "tool":
            arguments = json.loads(argv[3]) if len(argv) > 3 else {}
            value, content = mcp.tool(argv[2], arguments)
            images = sum(1 for block in content if block.get("type") == "image")
            print(text_of(value, int(argv[4]) if len(argv) > 4 else 12000))
            if images:
                print("(%d image block(s) not shown: use shot for pictures)" % images)
        elif command == "py":
            source = sys.stdin.read() if argv[2] == "-" else open(argv[2], encoding="utf-8").read()
            print(text_of(mcp.python(source), int(argv[3]) if len(argv) > 3 else 12000))
        elif command == "level":
            value, _ = mcp.tool("EditorToolset.LevelToolset.GetCurrentLevel", {})
            print(text_of(value, 400))
        elif command == "shot":
            options = {"exec": []}
            for item in argv[3:]:
                key, _, value = item.partition("=")
                if key == "exec":
                    options["exec"].append(value)
                else:
                    options[key] = value
            line, verdict = shot(mcp, argv[2], options)
            print(line)
            return 0 if verdict == "OK" else 4
        else:
            print(__doc__)
            return 2
    except McpError as error:
        print("MCP ERROR: " + str(error))
        return 1
    except (OSError, ValueError) as error:
        print("MCP UNREACHABLE or bad answer (%s): is the editor running? (editor.sh status)" % str(error)[:300])
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
