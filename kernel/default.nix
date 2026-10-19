# SPDX-License-Identifier: GPL-2.0-only
# Adapted for this single kernel profile; see NOTICE.md for provenance.
{
  lib,
  buildLinux,
  fetchurl,
  applyPatches,
  kernelPatches,
}:
let
  sources = lib.importJSON ./sources.json;
  configFile = fetchurl {
    name = "config";
    url = "https://raw.githubusercontent.com/CachyOS/linux-cachyos/${sources.configRev}/linux-cachyos-server/config";
    hash = sources.configHash;
  };
  src = applyPatches {
    name = "linux-src-patched";
    src = fetchurl {
      url = "https://github.com/CachyOS/linux/releases/download/${sources.release}/${sources.release}.tar.gz";
      hash = sources.sourceHash;
    };
    patches = [
      kernelPatches.bridge_stp_helper.patch
      kernelPatches.request_key_helper.patch
      ../patches/ath12k-wcn7850-5ghz-scan.patch
    ];
    prePatch = "";
    postPatch = ''
      install -Dm644 ${configFile} arch/x86/configs/cachyos_defconfig
    '';
  };
in
buildLinux {
  pname = "linux-cachyos-server";
  inherit (sources) version;
  inherit src;
  modDirVersion = "${sources.version}-cachyos";
  defconfig = "cachyos_defconfig";
  autoModules = true;
  ignoreConfigErrors = true;
  structuredExtraConfig = import ./config.nix { inherit lib; };
  extraMeta = {
    description = "CachyOS server kernel with MSI MS-7E79 hardware fixes";
    platforms = [ "x86_64-linux" ];
  };
}
