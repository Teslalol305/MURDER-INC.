#!/bin/bash
# Copy placeholder art from the engine's first-person template into the project's Content folder:
# first-person arms and mannequins with their animations, the three weapon meshes, the prototyping meshes and
# materials, and the template's input assets. Nothing here is committed (Content/ is ignored except Data and Python).
# Idempotent: files that already exist are left alone. Run it while the editor is stopped (or restart the editor
# afterwards) so that the asset registry sees the new files.
# Not copied on purpose: the template's Blueprints, widgets and maps. Their parent classes are the template's C++
# classes (/Script/TP_FirstPerson...), which this project does not have.
# Usage: seed-content.sh
main() {
  . "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
  mi_become_ue4 "$@"
  local t=$MI_ENGINE/Templates c=$MI_PROJECT_DIR/Content
  [ -d "$t/TP_FirstPerson/Content" ] || mi_die "SEED FAILED: $t/TP_FirstPerson/Content is missing"
  local before after
  before=$(find "$c" -name '*.uasset' 2>/dev/null | wc -l)
  seed() {  # seed <source directory> <folder under Content>
    [ -d "$1" ] || { echo "  missing in this engine: ${1#$t/}"; return; }
    mkdir -p "$c/$2" && cp -rn "$1/." "$c/$2/" 2>/dev/null
  }
  seed "$t/TemplateResources/High/Characters/Content"       Characters
  seed "$t/TemplateResources/High/Input/Content"            Input
  seed "$t/TemplateResources/Standard/Weapons/Content"      Weapons
  seed "$t/TemplateResources/High/LevelPrototyping/Content" LevelPrototyping
  seed "$t/TP_FirstPerson/Content/FirstPerson/Anims"        FirstPerson/Anims
  seed "$t/TP_FirstPerson/Content/Variant_Shooter/Anims"    Variant_Shooter/Anims
  seed "$t/TP_FirstPerson/Content/Variant_Shooter/Input"    Variant_Shooter/Input
  mkdir -p "$c/FirstPerson" && cp -n "$t/TP_FirstPerson/Content/FirstPerson/"*.uasset "$c/FirstPerson/" 2>/dev/null
  after=$(find "$c" -name '*.uasset' | wc -l)
  echo "SEED OK $after assets in Content ($(( after - before )) new): /Game/Characters /Game/Weapons /Game/Input /Game/LevelPrototyping /Game/FirstPerson /Game/Variant_Shooter"
}
main "$@"; exit $?
