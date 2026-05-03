# ComfyUI-Mememizator
ComfyUI node to make memes and demotivators.

![Example](images/image01.png)

## Configuration

On first launch the config file will be saved to:

```text
ComfyUI/user/default/ComfyUI-Mememizator/config.json
```

Fonts referenced by templates are downloaded to:

```text
ComfyUI/user/default/ComfyUI-Mememizator/fonts/
```

For `Classic Demotivator`, the node expects `impact.ttf` and downloads it from:

```text
https://font.download/dl/font/impact.zip
```

`MememizatorSettings` node builds UI overrides for the main meme node. Connect it to the optional `settings` input on `Mememizator` node to override config values without editing JSON.

The settings node also includes a `template_name` dropdown. On the client side, it loads the current config and fills the other fields from the selected template.

Edit the user config to add or change templates. Template names from `templates[].name`
are shown in the node dropdown. After changing the list of templates, restart ComfyUI.

## Mememizator Combine Images

`Mememizator Combine Images` combines up to four input images into a single frame. Use it before `Mememizator` to make memes that consist of several panels or sequential frames.

The node supports `horizontal`, `vertical`, and `2x2` layouts, with optional maximum output size, background color, and padding settings.

![Combine Images workflow](images/image02.png)

## Example

![Example](examples/example.png)

Workflow can be used from the image above or downloaded from [examples/workflow_basic.json](examples/workflow_basic.json), [examples/workflow_settings.json](examples/workflow_settings.json), or [examples/workflow_combine.json](examples/workflow_combine.json).
