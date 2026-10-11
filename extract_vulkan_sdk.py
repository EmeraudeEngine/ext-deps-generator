#!/usr/bin/env python3
"""
Extracts the strict minimum of an INSTALLED LunarG Vulkan SDK into the output/ directories.

The Vulkan SDK is not built from source like the registry libraries: the owner decision (2026-10-11) is to take
the files the SDK of each OS ships (the same version on the three OS), put them under

    output/<os>.<arch>-<cfg>[-<tag>]/vulkan-sdk/
        VERSION          the SDK version and where it was extracted from
        include/         vulkan/*.h and vk_video/*.h (the C headers only, no vulkan.hpp)
        lib/             what a consumer LINKS against: libvulkan.so (Linux), vulkan-1.lib (Windows),
                         libvulkan.1.dylib + libMoltenVK.dylib (macOS)
        layers/          the Khronos validation layer + its manifest (library_path relative to the manifest)
        icd/             macOS only: MoltenVK_icd.json (library_path ../lib/libMoltenVK.dylib)
        LICENSES/        the SDK licence files

and let the usual packaging zip output/ (or a developer symlink it into emeraude-base/dependencies/).

Usage:
    python3 extract_vulkan_sdk.py                      # the host SDK, every output/<host os>.* directory
    python3 extract_vulkan_sdk.py --sdk PATH --output output/linux.x86_64-Release-glibc2.41

The Vulkan loader itself is deliberately NOT shipped on Linux / Windows: CEF ships its own next to the application
(libvulkan.so.1 1.4.361 measured on Linux, 2026-10-11) and the application directory wins. macOS has no system
loader, so the SDK's is extracted there.
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

SDK_VERSION = "1.4.363.0"
VALIDATION_LAYER = "VK_LAYER_KHRONOS_validation"
ROOT = Path(__file__).resolve().parent


def host_os() -> str:
	system = platform.system()

	if system == "Linux":
		return "linux"

	if system == "Darwin":
		return "macos"

	if system == "Windows":
		return "windows"

	sys.exit(f"Unsupported host system '{system}'.")


def default_sdk_root(osname: str) -> Path:
	if osname == "linux":
		return Path.home() / "VulkanSDK" / SDK_VERSION / "x86_64"

	if osname == "macos":
		return Path.home() / "VulkanSDK" / SDK_VERSION / "macOS"

	return Path("C:/VulkanSDK") / SDK_VERSION


def find_one(root: Path, patterns: list[str], what: str, missing: list[str]) -> Path | None:
	for pattern in patterns:
		matches = sorted(root.glob(pattern))

		if matches:
			return matches[0]

	missing.append(f"{what} (searched {', '.join(patterns)} under {root})")

	return None


def copy_headers(sdk: Path, destination: Path, missing: list[str]) -> None:
	include = find_one(sdk, ["include", "Include"], "the include directory", missing)

	if include is None:
		return

	for subdirectory in ("vulkan", "vk_video"):
		source = include / subdirectory

		if not source.is_dir():
			missing.append(f"{source}")
			continue

		target = destination / "include" / subdirectory
		target.mkdir(parents=True, exist_ok=True)

		for header in sorted(source.glob("*.h")):
			shutil.copy2(header, target / header.name)


def copy_preserving_links(source: Path, target_directory: Path) -> None:
	"""Copies a library and the chain of symbolic links that names it (libvulkan.so -> .so.1 -> .so.1.4.363)."""
	target_directory.mkdir(parents=True, exist_ok=True)
	chain = []
	current = source

	while current.is_symlink():
		chain.append(current)
		current = current.parent / os.readlink(current)

	shutil.copy2(current, target_directory / current.name)

	for link in reversed(chain):
		destination = target_directory / link.name

		if destination.exists() or destination.is_symlink():
			destination.unlink()

		os.symlink(os.readlink(link), destination)


def output_architecture(output: Path) -> str:
	"""The architecture of an output directory: 'macos.arm64-Release-sdk12.0' -> 'arm64'."""
	return output.name.split("-", 1)[0].split(".", 1)[1]


def strip_binary(path: Path, osname: str, architecture: str) -> None:
	"""
	The SDKs ship their binaries unstripped (Linux validation layer 393 MB -> 32 MB, 2026-10-11).
	macOS: universal x86_64 + arm64 Mach-O files with debug stabs (validation layer 72 MB): thinned to the output's
	architecture, stripped of debug and local symbols, then RE-SIGNED ad hoc — any modification invalidates the
	signature, and Apple Silicon refuses to load an unsigned Mach-O. Windows: the DLL is copied as shipped.
	"""
	if osname == "linux":
		subprocess.run(["strip", "--strip-unneeded", str(path)], check=True)
	elif osname == "macos":
		architectures = subprocess.run(["lipo", "-archs", str(path)], check=True, capture_output=True, text=True).stdout.split()

		if architecture not in architectures:
			sys.exit(f"{path}: no {architecture} slice (it has {', '.join(architectures)}).")

		if len(architectures) > 1:
			subprocess.run(["lipo", str(path), "-thin", architecture, "-output", str(path)], check=True)

		subprocess.run(["strip", "-S", "-x", str(path)], check=True)
		subprocess.run(["codesign", "--force", "--sign", "-", str(path)], check=True, capture_output=True)


def write_manifest(source_manifest: Path, destination_manifest: Path, library_path: str) -> None:
	with open(source_manifest, encoding="utf-8") as file:
		manifest = json.load(file)

	key = "layer" if "layer" in manifest else "ICD"

	if key not in manifest:
		sys.exit(f"{source_manifest}: neither a layer nor an ICD manifest.")

	manifest[key]["library_path"] = library_path

	destination_manifest.parent.mkdir(parents=True, exist_ok=True)

	with open(destination_manifest, "w", encoding="utf-8", newline="\n") as file:
		json.dump(manifest, file, indent=4)
		file.write("\n")


def extract(sdk: Path, output: Path, osname: str) -> None:
	destination = output / "vulkan-sdk"
	architecture = output_architecture(output)

	if destination.exists():
		shutil.rmtree(destination)

	destination.mkdir(parents=True)
	missing: list[str] = []

	copy_headers(sdk, destination, missing)

	lib = destination / "lib"
	layers = destination / "layers"

	if osname == "linux":
		loader = find_one(sdk, ["lib/VulkanLoader/lib/libvulkan.so", "lib/libvulkan.so"], "libvulkan.so (link library)", missing)
		layer = find_one(sdk, ["lib/libVkLayer_khronos_validation.so"], "the validation layer", missing)
		manifest = find_one(sdk, ["share/vulkan/explicit_layer.d/VkLayer_khronos_validation.json"], "the validation layer manifest", missing)

		if loader:
			copy_preserving_links(loader, lib)
	elif osname == "windows":
		loader = find_one(sdk, ["Lib/vulkan-1.lib"], "vulkan-1.lib (link library)", missing)
		layer = find_one(sdk, ["Bin/VkLayer_khronos_validation.dll"], "the validation layer", missing)
		manifest = find_one(sdk, ["Bin/VkLayer_khronos_validation.json"], "the validation layer manifest", missing)

		if loader:
			lib.mkdir(parents=True, exist_ok=True)
			shutil.copy2(loader, lib / loader.name)
	else:
		loader = find_one(sdk, ["lib/libvulkan.dylib", "lib/libvulkan.1.dylib"], "libvulkan.dylib (loader)", missing)
		moltenvk = find_one(sdk, ["lib/libMoltenVK.dylib"], "libMoltenVK.dylib", missing)
		icd = find_one(sdk, ["share/vulkan/icd.d/MoltenVK_icd.json"], "the MoltenVK ICD manifest", missing)
		layer = find_one(sdk, ["lib/libVkLayer_khronos_validation.dylib"], "the validation layer", missing)
		manifest = find_one(sdk, ["share/vulkan/explicit_layer.d/VkLayer_khronos_validation.json"], "the validation layer manifest", missing)

		if loader:
			copy_preserving_links(loader, lib)

			for copied in lib.glob("libvulkan*.dylib"):
				if not copied.is_symlink():
					strip_binary(copied, osname, architecture)

		if moltenvk:
			lib.mkdir(parents=True, exist_ok=True)
			shutil.copy2(moltenvk, lib / moltenvk.name)
			strip_binary(lib / moltenvk.name, osname, architecture)

		if icd:
			write_manifest(icd, destination / "icd" / "MoltenVK_icd.json", "../lib/libMoltenVK.dylib")

	if layer and manifest:
		layers.mkdir(parents=True, exist_ok=True)
		shutil.copy2(layer, layers / layer.name)
		strip_binary(layers / layer.name, osname, architecture)
		write_manifest(manifest, layers / manifest.name, f"./{layer.name}")

	licences = destination / "LICENSES"
	licences.mkdir(parents=True, exist_ok=True)

	for candidate in [sdk / "LICENSE.txt", sdk.parent / "LICENSE.txt", sdk / "Licenses", sdk.parent / "Licenses"]:
		if candidate.is_file():
			shutil.copy2(candidate, licences / candidate.name)
		elif candidate.is_dir():
			shutil.copytree(candidate, licences / candidate.name, dirs_exist_ok=True)

	if not any(licences.iterdir()):
		missing.append("the SDK licence file (LICENSE.txt or Licenses/)")

	if missing:
		shutil.rmtree(destination)
		sys.exit("Vulkan SDK extraction refused, missing:\n  - " + "\n  - ".join(missing))

	with open(destination / "VERSION", "w", encoding="utf-8", newline="\n") as file:
		file.write(f"{SDK_VERSION}\nextracted from {sdk}\n")

	size = sum(path.stat().st_size for path in destination.rglob("*") if path.is_file() and not path.is_symlink())
	print(f"{destination}: {size / (1024 * 1024):.1f} MiB")

	for path in sorted(destination.rglob("*")):
		if path.is_file() and path.parent.name != "vulkan" and path.parent.name != "vk_video":
			print(f"  {path.relative_to(destination)}  {path.stat().st_size // 1024} KiB")


def main() -> None:
	osname = host_os()
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("--sdk", type=Path, default=default_sdk_root(osname), help="the installed SDK root for this OS")
	parser.add_argument("--output", type=Path, action="append", help="an output/<config> directory (repeatable); default: every output/<host os>.* directory")
	arguments = parser.parse_args()

	if not arguments.sdk.is_dir():
		sys.exit(f"The Vulkan SDK {SDK_VERSION} is not at '{arguments.sdk}' (use --sdk).")

	outputs = arguments.output or sorted(path for path in (ROOT / "output").glob(f"{osname}.*") if path.is_dir())

	if not outputs:
		sys.exit(f"No output/{osname}.* directory to extract into.")

	for output in outputs:
		extract(arguments.sdk, output, osname)


if __name__ == "__main__":
	main()
