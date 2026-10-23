"""Build agent_cooldowns.pack.

usage: python -m tools.build [--install]

Writes dist/agent_cooldowns.pack and its Workshop preview dist/agent_cooldowns.png;
--install copies both into the game's data folder.
"""
import shutil
import sys

from tools.packfile import write_pack
from tools.paths import GAME_DATA, ROOT
from tools.preview import make_preview, save_preview
from tools.render import render_mct_settings, render_script

PACK_NAME = "agent_cooldowns.pack"
PREVIEW_NAME = "agent_cooldowns.png"
SCRIPT_PATH = "script/campaign/mod/agentcd.lua"
MCT_PATH = "script/mct/settings/agentcd.lua"


def build(out_path):
    script = (ROOT / "src" / SCRIPT_PATH).read_text(encoding="utf-8")
    mct = (ROOT / "src" / MCT_PATH).read_text(encoding="utf-8")
    files = {
        SCRIPT_PATH: render_script(script).encode("utf-8"),
        MCT_PATH: render_mct_settings(mct).encode("utf-8"),
    }
    write_pack(out_path, files)
    return files


def main(argv, dist=ROOT / "dist"):
    dist.mkdir(exist_ok=True)
    build(dist / PACK_NAME)
    save_preview(make_preview(), dist / PREVIEW_NAME)
    print("built %s and %s" % (dist / PACK_NAME, dist / PREVIEW_NAME))
    if "--install" in argv:
        for name in (PACK_NAME, PREVIEW_NAME):  # the launcher wants the preview next to the pack
            shutil.copyfile(dist / name, GAME_DATA / name)
            print("installed %s" % (GAME_DATA / name))


if __name__ == "__main__":
    main(sys.argv[1:])
