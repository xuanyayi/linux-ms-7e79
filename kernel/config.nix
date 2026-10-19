# SPDX-License-Identifier: GPL-2.0-only
# Preserve the previous profile's settings; see NOTICE.md for provenance.
{ lib }:
let
  inherit (lib.kernel)
    yes
    no
    freeform
    option
    ;
in
{
  # Keep NixOS's compatibility settings alongside the official CachyOS defconfig.
  NR_CPUS = lib.mkForce (option (freeform "8192"));
  LOCALVERSION = freeform "-cachyos";
  OVERLAY_FS = lib.kernel.module;
  OVERLAY_FS_REDIRECT_DIR = no;
  OVERLAY_FS_REDIRECT_ALWAYS_FOLLOW = yes;
  OVERLAY_FS_INDEX = no;
  OVERLAY_FS_XINO_AUTO = no;
  OVERLAY_FS_METACOPY = no;
  OVERLAY_FS_DEBUG = no;
  HID = yes;
  ATH_REG_DYNAMIC_USER_REG_HINTS = yes;
}
// lib.mapAttrs (_: lib.mkForce) {
  CACHY = yes;
  MQ_IOSCHED_ADIOS = yes;

  # GCC, generic x86-64, EEVDF (no alternative scheduler enabled here).
  LTO_NONE = yes;
  LTO_CLANG_THIN = no;
  LTO_CLANG_FULL = no;
  GENERIC_CPU = yes;
  MZEN4 = no;
  X86_NATIVE_CPU = no;
  X86_64_VERSION = freeform "1";
  CC_OPTIMIZE_FOR_PERFORMANCE = no;
  CC_OPTIMIZE_FOR_PERFORMANCE_O3 = yes;

  HZ_300 = yes;
  HZ = freeform "300";
  HZ_PERIODIC = no;
  NO_HZ_IDLE = no;
  CONTEXT_TRACKING_FORCE = no;
  NO_HZ_FULL_NODEF = yes;
  NO_HZ_FULL = yes;
  NO_HZ = yes;
  NO_HZ_COMMON = yes;
  CONTEXT_TRACKING = yes;

  PREEMPT_DYNAMIC = yes;
  PREEMPT = no;
  PREEMPT_VOLUNTARY = no;
  PREEMPT_LAZY = yes;
  PREEMPT_NONE = no;

  TRANSPARENT_HUGEPAGE_MADVISE = no;
  TRANSPARENT_HUGEPAGE_ALWAYS = yes;
}
