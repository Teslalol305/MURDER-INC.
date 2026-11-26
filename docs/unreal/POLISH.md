# POLISH: what nobody had listed yet

Read-only audit (no GPU box): code, data and the recent pictures. Items already in READY, SMOOTH, PLAY and HANDS_R4 are excluded.
29 findings were raised; 4 were rejected by review, 25 are kept below. Severities are the reviewers' downgraded ratings.
Nothing here is verified on a running build. Items marked (code only) rest on reading source and data, not on a capture.

Rejected, with reason:
- Pause footer says "browser": true for a streamed build, Esc does release the browser's pointer lock. Not a defect.
- Rack "Carried - slot n" cut and Block & Style title wrap: already READY M1/M5.
- "Controls tab promises arrow/IJKL turning": the `note` key is never drawn and nothing reads `hints.drag`, so players are not misled. (The missing key-turn itself is an optional feature, see decisions.)
- AZERTY/Dvorak keys: unproven, depends on what E3DS sends. One line on the page ("assumes QWERTY") is the only cheap action.

## Summary

The game's rules and data are in good shape. What is left is mostly feel and presentation: damage feedback that vanishes too fast, kills by explosion that give no confirmation, goons that take hits without reacting, and a HUD where most text does not scale with resolution. There is also one state (no gun carried) where the NEXT button disappears, and a block of dead web-game copy in text.json. Seven items are safe for v6; the rest are tuning or feature work for the next release.

## Backlog (priority order)

Effort: S under 1 h, M half a day, L a day or more. Slot: v6 = cheap and safe, next = next release, owner = needs a decision first.

| # | Sev | Area | Finding | Evidence | Fix | Effort | Slot |
|---|-----|------|---------|----------|-----|--------|------|
| 1 | should-fix | Hit feedback | Damage-direction wedge vanishes in 0.2-0.5 s, designed 1.5 s | MIHUD.cpp:189 `if (Hurt <= 0.0) return;` runs before the wedge code; wedge timer at :212. Hurt = 0.35 + 0.025*dmg (MIPlayerRules.cpp:213), decays 1.9/s, so a 4-damage round is gone in 0.24 s | Move wedge block above the early return or give it its own timer; hold 1-1.5 s with fade; one wedge per attacker | S | v6 |
| 2 | should-fix | Kill feedback | Blast kills give no hit marker, hit tick or kill tick | PlayerHitEnemy and NoteHit fire only in MIWeaponComponent.cpp:584 (Hitscan) and :661 (Melee); MICombatSubsystem::Explode (:107) never raises them | In Explode, for enemies the player caused, call NoteHit and broadcast PlayerHitEnemy (bKilled, part "blast"), once per victim per blast | S | v6 |
| 3 | should-fix | Front end | NEXT button label invisible when no gun carried | SMIFrontEnd.cpp:486-490 label is `Bg()` on the Primary disabled brush (Plate at 0.4 alpha, line 127); MIFrontEndRules.cpp:77-83 blocks Loadout with zero guns. No shot covers it | State-aware label colour (InkFaint when disabled) and a visible disabled fill (Gold at 0.25 plus edge); add a MIShot of the empty-loadout state | S | v6 |
| 4 | should-fix | Settings | Sliders move one tiny step per press: volume 0.01, no repeat, no drag, no pad step | rules.json:15-17 (sensStep 0.05, volumeStep 0.01); MIGameSubsystem.cpp:672-674 MenuAdjust; Left/Right Started-only (MIPlayerController.cpp:125-126); stream drops held-pad repeats (MICloud.cpp:1306). Volume 0.8 to 0.2 = 60 presses. spec/07-ui-audio.md:361 says pad steps were 0.1 / 5% | padStep values in rules.json used when a pad is active; auto-repeat (0.38 s then 0.17 s) on held Left/Right; click position on the slider sets the value | M | v6 (steps) / next (drag) |
| 5 | should-fix | HUD | Only the objective title scales with resolution | MIHUD.cpp:508-548: hold prompt 1.3f, warning 1.6f, message 1.2f, location card 1.6f with +40 px tagline, markers 1.1f / Pad 5, radio 1.1f are literal; weapon strip and health use K = H/1080. Stream is clamped to 1080p (READY R1), so it bites windowed/720p | `const double K = H/1080` in DrawFlow; multiply every scale and pixel offset; derive tagline offset from measured text height | M | v6 |
| 6 | should-fix | HUD | Warnings, hold prompt, messages and location card have no plate and use engine Roboto | Plain Centered() text with the large engine font; objective, radio and markers have 0.42-0.5 alpha bands (code only; contrast claim not viewed) | Route through MIStyle CanvasDisplay/CanvasBody and the same band helper, or a dark drop shadow; gold rule on the location card | M | v6 |
| 7 | should-fix | Feel | Goon flinch computed, never drawn | MIEnemies.cpp:385-392 sets FlinchStrength/Age/Dir; only reader is the rules file; AMIGoon never reads it. Goons take 4-6 rounds with no body reaction | Read the flinch values in AMIGoon::Sync; additive upper-body or procedural bone offset decaying over ~0.2 s plus a small actor push | M | next |
| 8 | should-fix | Optics | "4x scope" is about 1.8x over the irons | attachments.json:426 adsFov 30; config.json:125 ads 52; tan26/tan15 = 1.82 (2.8x vs hip). frontend_text.json:146 says "four times the reach". Tube look not viewed | Rename "2x scope" or set adsFov ~18-20 for a true 3-4x; thin the tube ring | S (data) | owner |
| 9 | should-fix | Camera | Base FOV is 106 deg horizontal at 16:9 (112 sprinting) | config.json:121-125 base 74 vertical; MIPlayerCharacter.cpp:558-570 converts with live aspect; rules.json range 60-95 vertical | Lower default to ~66-68 vertical, or clamp horizontal to ~105; show horizontal degrees in the Settings label | S | owner |
| 10 | should-fix | Controller | A pad that disconnects mid-run is not handled | No disconnect handler: only OnAllViewersLeft (MICloud.cpp:1138-1175) and OnViewerAway release input; FMIPadButtons keeps a button down so the next press is dropped (:1306); spec/04-flow.md:1319 lists disconnect as a pause trigger (code only; plugin message unverified) | Handle the plugin disconnect message: reset PadButtons, stick, nav, zero axes, pause the run; add a MurderInc.Cloud.PadDisconnect test | M | next |
| 11 | nit | Front end | Pick-one screens with one option | levels.json:17 times ["day"]; one crew card (ready-menu-crew.jpg); Picker rows still focus stops | Render single-entry lists as static info and skip them in NumFocusable; collapse Crew step until a second crew exists | S-M | v6 (focus skip) / owner (Crew) |
| 12 | nit | Audio | Four guns reuse the CHOPPER sound | audio.json:178-181 maps shorty, stick, stretch, rattler to chopper; no pitch/vol offset in the mapping. Deliberate placeholder (data "about"), guarded by EveryGunSounds | Extend weaponSounds to {sound, pitch, vol, tail}; RATTLER up ~12-15%, STRETCH down | S | v6 (data only) |
| 13 | nit | Feel | Headshot marker identical to body hit | WasLastHitHead() (MIWeaponComponent.h:57) has no caller; MIHUD.cpp:117-125 one fixed X; hit_head audio peak 0.37 | Bigger, longer marker for head, heavier red for kill; 60 ms pop-in; 2-3 hit_confirm variants with pitch jitter | S | v6 |
| 14 | nit | Feel | Recoil and ADS spread very mild | config.json:286, :363: pitch 0.0068 chopper, x0.55 ADS, 0.38 late; ADS spread 6 to 4 cm at 50 m vs head radius 15.5 cm. Computed, no spray capture. Web-parity values, deliberately untouched | Capture a spray on the box first; if confirmed, raise rifle recoil.pitch 1.5-2x or ADS bloom | S (data) | owner |
| 15 | nit | Front end | Pause/stream hints stack two lines | MIHUD.cpp:~612-619 card hint plus MICloud.cpp:569 "P to resume..." line; diagnostics line is READY M8 | Merge into one hint naming the stream key (P / START) | S | v6 |
| 16 | nit | HUD | Crosshair is a thin 85% white cross with no outline, fixed 2 px | MIHUD.cpp:~100-112 four DrawRect arms; hit marker uses DrawLine | 4 px dark underlay (0.45 alpha) per arm; scale thickness and length with K | S | v6 |
| 17 | nit | HUD | Death card hint overprinted by a tiny second line | e2e-deaths-pause.jpg panel 3 shows it; cause unconfirmed, may be the harness overlay | Capture a clean Shipping build; if it persists, find the second draw on the Dead state | S | v6 (verify first) |
| 18 | nit | Front end | Click-to-play card stacks a second wordmark and mixed type sizes | MICloud.cpp:~537-560; cloud-click-to-play.jpg | Drop the card wordmark or make the veil near-opaque; one body size; key plates for WASD | S | v6 |
| 19 | nit | Controller | One Sensitivity and Invert Y drive mouse and right stick | MIPlayerController.cpp:534 and :605; PREFLIGHT.md:140 tells players to cut sensitivity to 0.35-0.5, which also slows the stick | Pad-only rows: look speed, invert Y, dead zone (config.json pad block holds the defaults) | M | next |
| 20 | nit | Robustness | Failed boot is silent in Shipping | MIGameMode.cpp:41 drops Boot()'s bool; Boot returns false at MIGameSubsystem.cpp:143 and :161 after UE_LOG only; Shipping compiles UE_LOG out (MICloud.cpp:85-93) | MI_LOG_ALWAYS macro (printf fallback like MICloudPrivate::Line); check Boot result and show a "data failed to load" card | M | next |
| 21 | nit | Text | Dead web-game copy in the data | text.json 218, 328, 365, 491-497 and config.json:189 (title.note, boot.*, page.*, input.hints, panel.fullscreen*); no code reads them | Delete from text.json and shipped data if the data-load tests do not require the keys | S | v6 |
| 22 | nit | Text | Hard-coded English and an unused string | MIMenus.cpp:90 "Controller/PlayStation/Xbox", :93 "Ground path" (READY M11 covers the row); MIHUD.cpp:166 literal "HEALTH" while text.json hud.hp "HP" (line 423) is never read; hint strings MIHUD.cpp:~612-619 | Move hint strings into text.json; pick HP or HEALTH and use the table | S | v6 |
| 23 | nit | Text | Casing and naming drift | "Silencer" (frontend_text.json:134) vs "Suppressor" (:147); where.title "Block and style" (:419) vs step label "Block & Style"; summary and compass casing | Rename to Suppressor; one name "Block & Style"; one casing rule for summary and compass | S | v6 |
| 24 | nit | Text | STRETCH blurb says it hits harder | guns.json stretch damage 25, 700 rpm vs chopper 26, 720 (config.json). "Harder" is true only against the STICK (21). guns.json:827 acknowledges the 10-round mag art | Reword to "longer reach, steadier" | S | v6 |
| 25 | nit | Text | Attachment blurbs vs data | mag_standard has effects [] (attachments.json:333-343) so "Thirty rounds, steel" is flavour; magClear (frontend_text.json:142) omits the 6% faster reload; laser and red dot hide the aimed spread penalty (x1.1 / x1.08) | Add "reloads quicker" to magClear and "a little looser when aimed" to laser and red dot | S | v6 |

## v6 shortlist (cheap and safe)

Items 1, 2, 3, 5, 6, 13, 15, 16, 18, 21, 22, 23, 24, 25, the data-only parts of 4 and 12, and the focus-skip part of 11. Items 1, 2 and 3 matter most.
Before touching 17, get one clean Shipping capture to see whether the overprint is real.

## Owner decisions needed

1. Scope power: rename to "2x scope" or lower adsFov to ~18-20 for a true 3-4x (#8).
2. Field of view: keep 74 vertical (106 deg horizontal) as web parity, or lower the default to ~66-68 (#9).
3. Recoil tuning: ship web-parity values, or raise rifle recoil after a spray capture (#14).
4. Crew step: collapse or hide it until a second crew exists, and the single-entry TIME/level rows (#11).
5. Optional keyboard turning (Arrows / IJKL): the web spec had it and no Unreal code does. Build it as a fallback for players whose browser refuses pointer lock, or leave it out. Nothing on screen promises it today.
6. Gun sound identity: accept placeholder reuse of the CHOPPER shot until recorded material exists, or add per-gun pitch/tail now (#12).
7. Controller settings: whether pad look speed, invert and dead zone become Settings rows (#19), and whether pad disconnect should pause the run (#10).
8. Keyboard layout: confirm on E3DS what key an AZERTY or Dvorak player sends before spending time on a fallback table.
