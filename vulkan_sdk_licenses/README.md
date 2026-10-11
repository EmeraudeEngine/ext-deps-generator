# Licences of the Vulkan SDK components shipped in `output/<cfg>/vulkan-sdk/`

LunarG's own `LICENSE.txt` (copied from the installed SDK) states that the SDK carries no licence of its own: every
component keeps its own. `extract_vulkan_sdk.py` copies this directory into `vulkan-sdk/LICENSES/` next to it, so each
archive carries the licence of everything it redistributes. Fetched from the upstream repositories at the tag matching
`SDK_VERSION` (update them together).

| Directory | Redistributed in `vulkan-sdk/` | Licence | Source |
|---|---|---|---|
| `Vulkan-Headers/` | `include/vulkan`, `include/vk_video` | Apache-2.0 OR MIT (`LICENSE.md`, `LICENSES/`) | KhronosGroup/Vulkan-Headers @ vulkan-sdk-1.4.363.0 |
| `Vulkan-Loader/` | `lib/` loader (libvulkan / vulkan-1) | Apache-2.0 | KhronosGroup/Vulkan-Loader @ vulkan-sdk-1.4.363.0 |
| `Vulkan-ValidationLayers/` | `layers/` VK_LAYER_KHRONOS_validation | Apache-2.0 (+ the more permissive exceptions it lists) | KhronosGroup/Vulkan-ValidationLayers @ vulkan-sdk-1.4.363.0 |
| `SPIRV-Tools/` | linked into the validation layer | Apache-2.0 | KhronosGroup/SPIRV-Tools @ vulkan-sdk-1.4.363.0 |
| `SPIRV-Headers/` | used by the validation layer | MIT-style Khronos licence | KhronosGroup/SPIRV-Headers @ vulkan-sdk-1.4.363.0 |
| `MoltenVK/` | macOS only: `lib/libMoltenVK.dylib`, `icd/` | Apache-2.0 | KhronosGroup/MoltenVK @ v1.4.2 (same text in v1.4.1) |
