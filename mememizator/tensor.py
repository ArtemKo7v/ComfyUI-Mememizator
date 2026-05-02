from .dependencies import require_numpy, require_pillow, require_torch


# Converts a ComfyUI image tensor to a PIL image.
def tensor_to_pil(image_tensor):
    Image, _, _, _ = require_pillow()
    torch = require_torch()

    tensor = image_tensor.detach().cpu()
    if tensor.ndim != 3:
        raise RuntimeError(f"Expected an IMAGE tensor with 3 dimensions, got shape {tuple(tensor.shape)}")

    if tensor.shape[-1] == 4:
        tensor = tensor[..., :3]
    elif tensor.shape[-1] == 1:
        tensor = tensor.repeat(1, 1, 3)
    elif tensor.shape[-1] != 3:
        raise RuntimeError(f"Unsupported channel count {tensor.shape[-1]} for meme generation")

    tensor = tensor.to(dtype=torch.float32).clamp(0.0, 1.0)
    np = require_numpy()
    array = (tensor.numpy() * 255.0).round().astype(np.uint8)
    return Image.fromarray(array, mode="RGB")


# Converts a PIL image to a ComfyUI image tensor.
def pil_to_tensor(image):
    torch = require_torch()
    np = require_numpy()

    array = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    return torch.from_numpy(array)


