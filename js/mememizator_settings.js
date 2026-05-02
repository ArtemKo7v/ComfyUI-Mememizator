import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const NODE_CLASS = "ArtemKo7vMememizatorSettings";
const TEMPLATE_DEFAULT_FONT = "(template default)";
const CONFIG_ROUTE = "/artemko7v/mememizator/config";
let templateMapPromise = null;

// Finds a widget on a node by name.
function findWidget(node, name) {
  return node.widgets?.find((widget) => widget.name === name);
}

// Sets a widget value when the widget exists.
function setWidgetValue(node, name, value) {
  const widget = findWidget(node, name);
  if (!widget || value === undefined) {
    return;
  }
  widget.value = value;
}

// Loads the template map from the backend config route.
async function loadTemplateMap() {
  if (!templateMapPromise) {
    templateMapPromise = api.fetchApi(CONFIG_ROUTE)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        const map = new Map();
        for (const template of data?.templates ?? []) {
          if (template?.name) {
            map.set(template.name, template);
          }
        }
        return map;
      })
      .catch((error) => {
        console.error("[ComfyUI-Mememizator] Failed to load config for settings node", error);
        templateMapPromise = null;
        return new Map();
      });
  }

  return templateMapPromise;
}

// Converts a template config into settings widget values.
function getTemplateWidgetValues(template, fontOptions) {
  const imageOffset = template.image_offset ?? {};
  const frame = template.frame ?? {};
  const textArea = template.text_area ?? {};
  const textOutline = template.text_outline ?? {};
  const canvasExtra = template.canvas_extra ?? {};
  const title = template.title ?? {};
  const subtitle = template.subtitle ?? {};
  const fontCandidate = template.font?.font_candidates?.[0] ?? TEMPLATE_DEFAULT_FONT;
  const normalizedFont = fontOptions.includes(fontCandidate) ? fontCandidate : TEMPLATE_DEFAULT_FONT;

  return {
    background: template.background_color ?? "",
    text: template.text_color ?? "",
    padding_x: imageOffset.x ?? -1,
    padding_y: imageOffset.y ?? -1,
    frame_color: frame.color ?? "",
    frame_gap: frame.gap ?? -1,
    frame_thickness: frame.thickness ?? -1,
    text_padding_x: textArea.padding_x ?? -1,
    text_padding_bottom: textArea.padding_bottom ?? -1,
    text_position: textArea.position ?? "below",
    outline_color: textOutline.color ?? "#000000",
    outline_thickness: textOutline.thickness ?? -1,
    gap_from_image: textArea.gap_from_image ?? -1,
    block_spacing: textArea.block_spacing ?? -1,
    multiline_spacing: textArea.multiline_spacing ?? -1,
    extra_width: canvasExtra.width ?? -1,
    extra_height: canvasExtra.height ?? -1,
    title_size: title.size ?? -1,
    title_min_size: title.min_size ?? -1,
    subtitle_size: subtitle.size ?? -1,
    subtitle_min_size: subtitle.min_size ?? -1,
    font_name: normalizedFont,
  };
}

// Applies a selected template to a settings node.
async function applyTemplateToNode(node, templateName) {
  const templateMap = await loadTemplateMap();
  const template = templateMap.get(templateName);
  if (!template) {
    return;
  }

  const fontWidget = findWidget(node, "font_name");
  const fontOptions = Array.isArray(fontWidget?.options?.values) ? fontWidget.options.values : [TEMPLATE_DEFAULT_FONT];
  const values = getTemplateWidgetValues(template, fontOptions);

  for (const [name, value] of Object.entries(values)) {
    setWidgetValue(node, name, value);
  }

  node.setDirtyCanvas?.(true, true);
  app.graph?.setDirtyCanvas?.(true, true);
}

app.registerExtension({
  name: "artemko7v.mememizator.settings-template-sync",
  // Binds template synchronization when a settings node is created.
  async nodeCreated(node) {
    if (node.comfyClass !== NODE_CLASS || node.__mememizatorTemplateSyncBound) {
      return;
    }

    node.__mememizatorTemplateSyncBound = true;
    const templateWidget = findWidget(node, "template_name");
    if (!templateWidget) {
      return;
    }

    const originalCallback = templateWidget.callback;
    // Handles template widget changes and applies matching defaults.
    templateWidget.callback = async function (value, ...args) {
      if (originalCallback) {
        await originalCallback.call(this, value, ...args);
      }
      await applyTemplateToNode(node, value);
    };
  },
});
