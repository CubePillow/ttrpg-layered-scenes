# Test pictures for the pixelize test

Put your own PNG files here. The pictures are not in git, only this file is.

`tests/test_image_layers.py` sends every PNG in this folder to `POST /pixelize` and saves the results to `tests/output/`.
Without pictures the test is skipped.

## How to use

1. Copy layer pictures into this folder, for example the layers the prototype split (`prototype/scenes/<id>/*.png`).
2. In `backend/`, run:

   ```bash
   python -m pytest tests/test_image_layers.py
   ```

3. Look at `tests/output/`:

   | File | What it is |
   |---|---|
   | `<name>.png` | the pixel asset: 1 block = 1 pixel, transparent background, cut to its content |
   | `<name>_preview.png` | the same asset enlarged, for looking at |
   | `_compare_<width>x<height>.png` | every original next to its pixel version |

## Rules

- **PNG only.** Other formats are ignored.
- **Transparent background** for objects. A white or coloured backdrop is treated as part of the picture.
- **Pictures of the same size are processed together** and share one pixel grid and one palette, so put the layers
  of one scene in at a time. Pictures of another size form their own group.
- **A file whose name starts with `background` is the back layer** of its group. The others follow in name order.
- **The asset name is the part of the file name before `__`**: `campfire__v00-qwen21-extract.png` becomes `campfire.png`.
  A repeated name gets `-2`, `-3`, ...

Block size and number of colours are set at the top of the test file: `BLOCK, COLORS = 4, 16`.

## Which pictures work well

Simple pictures with large colour areas pixelize best. For generated pictures, add this to the prompt:

```
flat colour vector illustration, simple shapes, large colour blocks, few details
```

Photos, pencil drawings and other pictures with fine texture turn noisy.
