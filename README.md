# ComfyUI-Mememizator
ComfyUI node to make memes and demotivators.

## Configuration

The default template config is stored in the repository at:

```text
ComfyUI/custom_nodes/ComfyUI-Mememizator/config.json
```

On first launch it is copied to:

```text
ComfyUI/user/default/ComfyUI-Mememizator/config.json
```

Fonts referenced by templates are downloaded to:

```text
ComfyUI/user/default/ComfyUI-Mememizator/fonts/
```

For `Classic Demotivator`, the node expects `TR Impact.ttf` and downloads it from:

```text
https://font.download/dl/font/tr-impact.zip
```

`ArtemKo7vMememizatorSettings` builds UI overrides for the main meme node. Connect it to the optional `settings` input on `ArtemKo7vMememizator` to override config values without editing JSON.

Edit the user config to add or change templates. Template names from `templates[].name`
are shown in the node dropdown. After changing the list of templates, restart ComfyUI.