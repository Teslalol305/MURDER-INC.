#!/bin/bash
# Build the block in the running headless editor: Content/Python/build_block.py (import the art from
# /project/ue/art-in, make the materials, assemble /Game/Maps/L_Block). The work runs in editor ticks.
# Usage: block.sh start [steps] [force]   steps: all (default) or a comma list of textures,materials,meshes,level
#        block.sh status                  the progress file; the last line says DONE or FAILED when it has ended
#        block.sh wait                    status, after waiting up to 38 s for the job to end
main() {
  . "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
  mi_become_ue4 "$@"
  local st=$MI_PROJECT_DIR/Saved/BuildBlock/status.txt
  case "${1:-status}" in
    start)
      [ -n "$(mi_editor_pid)" ] || mi_die "BLOCK FAILED: the editor is not running (editor.sh start)"
      local steps=${2:-all} force=False
      [ "${3:-}" = force ] && force=True
      printf 'import importlib, sys, unreal\npath = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + "Python"\nsys.path.insert(0, path) if path not in sys.path else None\nimport build_block\nimportlib.reload(build_block)\nbuild_block.start("%s", force=%s)\n' "$steps" "$force" \
        | mi_mcp py - ;;
    wait)
      local i
      for i in $(seq 1 19); do tail -1 "$st" 2>/dev/null | grep -qE ' (DONE|FAILED) ' && break; sleep 2; done
      tail -n "${2:-12}" "$st" | cut -c1-400 ;;
    status)
      tail -n "${2:-12}" "$st" | cut -c1-400 ;;
    *) mi_die "usage: block.sh start [steps] [force] | status [lines] | wait [lines]" ;;
  esac
}
main "$@"; exit $?
