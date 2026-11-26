# Fonts kept with the art (art/blender/fonts)

Every typeface a sign, screen or label of the new levels is drawn with lives here, so an atlas rebuilt on any machine
draws the same letters (the atlas scripts read only this folder, never the system's fonts). All are under the SIL Open
Font License 1.1 (ART_BIBLE 5.6 allows OFL or Apache type only). Each file carries its copyright notice and its licence
in its own name table (name IDs 0, 13 and 14), which is how the OFL lets a font travel without a separate text file;
the three older faces also have their licence text beside them (OFL_*.txt).

| File | Family | Used for |
|---|---|---|
| InterDisplay-Black.otf, Inter-Bold.otf, Inter-SemiBold.otf, Inter-Light.otf, Inter-Italic.otf | Inter | modern lightboxes, sub-lines, street blades, Midtown's screens |
| Anton-Regular.ttf | Anton | tall condensed headlines (GOLD HITS, GOLDEN LUCK, KEYS CUT) |
| BebasNeue-Regular.ttf | Bebas Neue | condensed caps (SUNNY DAY, HARBOR STAR, SEVENTH AV SOUVENIRS) |
| ArchivoBlack-Regular.ttf | Archivo Black | wide heavy grocery and market bands (GOLDEN TIDE, GOOD WISHES, TWIN CARP) |
| AlfaSlabOne-Regular.ttf | Alfa Slab One | old painted slab signs (EIGHT TREASURE, JADE TEAPOT, the arcade arch) |
| FjallaOne-Regular.ttf | Fjalla One | narrow signwriting (WEST CITY, SEVEN STARS, FAR SHORE) |
| Kalam-Bold.ttf | Kalam | hand-painted stall boards and the marker placards |
| PassionOne-Bold.ttf | Passion One | rounded cafe and bakery signs (MOON GATE, LITTLE KITE, LONG LIFE) |
| Carlito-Bold.ttf | Carlito | spare (the placards' earlier face) |
| OldStandard-Bold.ttf | Old Standard | serif: banquet hall, herb shop, tailor, theatre, hotel, carved plaques |
| PinyonScript-Regular.ttf, UnifrakturMaguntia-Book.ttf | Pinyon Script, UnifrakturMaguntia | script lines on screens; the Block's blackletter |

Which face goes on which sign: `STYLE` in assets/_chinatown_names.py (Canal Street) and `font` in
assets/_midtown_names.py (Midtown). A new face is added here, with its licence checked, before an atlas uses it.
