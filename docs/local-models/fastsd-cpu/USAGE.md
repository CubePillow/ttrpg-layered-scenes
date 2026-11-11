# FastSD CPU: Prompts and Settings, Offline

Copy of the team's shared doc (https://claude.ai/artifact/3e64CqsdaqBJWTM5G2gJwE), synced 2026-11-09. Setup: [INSTALL.md](INSTALL.md). The tests behind these values: [log.md](../../log.md) (Phase 1) and [../../experiments/](../../../experiments).

## Overview

This guide shows how to generate images offline with FastSD CPU, using one of two models. Each path section below is complete on its own, so follow only the path you set up.

| Path | Model | Time per image | Notes |
| --- | --- | --- | --- |
| 1 | `models/sd-turbo` | about 20 s | Faster. At Strength 0.8 it can lose small details of the input image. |
| 2 | `models/sdxl-turbo` | about 58 s | Best at following both the prompt and the input image. |

Times were measured on a CPU-only laptop at 512 x 512.

Each path works in two ways:

- **Text to Image:** the prompt alone decides the picture. Style words show clearly, but the layout is not controlled.
- **Image to Image:** an input image sets layout and colours, and the prompt sets content and style. Use it when the composition matters.

**Before using a path,** complete its setup in the Install and Offline Setup guide ([INSTALL.md](INSTALL.md)): Part A, then Part B for Path 1 or Part C for Path 2.

## Writing prompts

Use one structure, and change only the style prefix to compare styles:

```
[style], [one main subject doing something], [placement and key objects], [setting], [lighting or mood]
```

Example:

```
watercolor painting, one red fox sitting next to a wooden cabin, cabin on the left side, snowy pine forest at dusk, soft warm light
```

Rules that held up in testing:

- Put the style words first.
- State the count ("one fox"). It reduces repeated subjects but does not prevent them, so try several seeds.
- Position words such as "on the left" are mostly ignored in Text to Image. To control layout, use Image to Image with an input drawn in that layout.
- Leave the negative prompt empty.
- Keep the prompt under about 50 words.
- Painterly styles such as impressionist or watercolor showed clearly. Pixel-art wording was only partly honoured.

## Path 1: SD-Turbo

Requires the Install guide, Parts A and B. Everything below is specific to Path 1.

### Start the app and set it up

**1.** In the `fastsdcpu` folder, double-click `start-webui-offline.bat`. No internet connection is needed.

**2.** Open <http://127.0.0.1:7860>.

**3.** Under **Mode**, select **LCM**.

**4.** Open **Models** and set **LCM model** to `models/sd-turbo`.

**5.** Open **Generation Settings** and set:

| Setting | Value |
| --- | --- |
| Inference Steps | 4 |
| Image Height / Width | 512 / 512 |
| Number of images to generate | 1 |
| Guidance Scale | 1 |
| Use seed | unticked |
| Use locally cached model or downloaded model folder(offline) | ticked |
| Use Safety Checker | unticked |
| Use Tiny AutoEncoder | unticked |

Settings reset when the app restarts, so repeat steps 3 to 5 each session.

### Text to Image

**1.** Open the **Text to Image** tab.

**2.** Paste your prompt (see Writing prompts). Leave the negative prompt empty.

**3.** Click **Generate**. The image appears under **Generated images** and is saved in `fastsdcpu\results`.

**4.** Click **Generate** again as often as you like. With **Use seed** unticked, each run uses a new random seed. Generate at least three images and pick the best.

### Image to Image

**1.** Prepare the input image:

- Use a PNG or JPG with a solid, non-transparent background, roughly square.
- Keep shapes simple and large.
- Colour the background and main objects as you want the result to look. A white background gives pale results, and a dark blue sky gives a night scene.
- Do not blur the image.

**2.** Open the **Image to Image** tab and upload your input image.

**3.** Paste your prompt. Leave the negative prompt empty.

**4.** Set **Strength** to 0.8 and click **Generate**.

**5.** Click **Generate** again as often as you like. With **Use seed** unticked, each run uses a new random seed. Generate at least three images and pick the best.

## Path 2: SDXL-Turbo

Requires the Install guide, Parts A and C. Everything below is specific to Path 2.

### Start the app and set it up

**1.** Close other large programs. SDXL-Turbo needs about 11 GB of free RAM.

**2.** In the `fastsdcpu` folder, double-click `start-webui-offline.bat`. No internet connection is needed.

**3.** Open <http://127.0.0.1:7860>.

**4.** Under **Mode**, select **LCM**.

**5.** Open **Models** and set **LCM model** to `models/sdxl-turbo`.

**6.** Open **Generation Settings** and set:

| Setting | Value |
| --- | --- |
| Inference Steps | 4 |
| Image Height / Width | 512 / 512 |
| Number of images to generate | 1 |
| Guidance Scale | 1 |
| Use seed | unticked |
| Use locally cached model or downloaded model folder(offline) | ticked |
| Use Safety Checker | unticked |
| Use Tiny AutoEncoder | unticked |

Settings reset when the app restarts, so repeat steps 4 to 6 each session.

### Text to Image

**1.** Open the **Text to Image** tab.

**2.** Paste your prompt (see Writing prompts). Leave the negative prompt empty.

**3.** Click **Generate**. The first image is slower because the model has to load into RAM. The image appears under **Generated images** and is saved in `fastsdcpu\results`.

**4.** Click **Generate** again as often as you like. With **Use seed** unticked, each run uses a new random seed. Generate at least three images and pick the best.

### Image to Image

**1.** Prepare the input image:

- Use a PNG or JPG with a solid, non-transparent background, roughly square.
- Keep shapes simple and large.
- Colour the background and main objects as you want the result to look. A white background gives pale results, and a dark blue sky gives a night scene.
- Do not blur the image.

**2.** Open the **Image to Image** tab and upload your input image.

**3.** Paste your prompt. Leave the negative prompt empty.

**4.** Set **Strength** to 0.8 and click **Generate**.

**5.** Click **Generate** again as often as you like. With **Use seed** unticked, each run uses a new random seed. Generate at least three images and pick the best.
