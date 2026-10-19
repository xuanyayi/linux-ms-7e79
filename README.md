# linux-ms-7e79

Custom Linux kernel builds for MSI MS-7E79 (MPG B850I EDGE TI WIFI).

Based on CachyOS server kernel, with hardware-specific fixes used by this system.

The Nix build recipe is maintained in this repository. Kernel sources and the
server configuration are fetched directly from the official CachyOS repositories;
Nixpkgs is independently pinned in `flake.lock`. No lantian/xddxdd flake or binary
cache is required.

## Configuration & Fixes

- **Kernel Profile**: CachyOS server kernel (`linux-cachyos-server`)
  - EEVDF scheduler
  - `CONFIG_PREEMPT_LAZY=y` with dynamic preemption
  - 300 Hz timer frequency (`CONFIG_HZ_300=y`)
  - Full dynamic tickless (`CONFIG_NO_HZ_FULL=y`)
  - GCC build (no LLVM LTO)
  - Standard server throughput-oriented baseline
- **Qualcomm WCN7850 Fixes**:
  - `CONFIG_ATH_REG_DYNAMIC_USER_REG_HINTS=y`: enables dynamic user regulatory domain hints in ath12k.
  - `ath12k-wcn7850-5ghz-scan.patch`: removes per-radio channel range check in `ath12k_reg_update_chan_list` to allow scanning 5 GHz channels.
- **Out-of-tree Modules**:
  - `nct6687d`: Super I/O hardware monitoring module built against this kernel ABI (`packages.x86_64-linux.nct6687d`).

## Usage in NixOS

### Binary Cache (Cachix)

```nix
nix.settings = {
  substituters = [
    "https://linux-ms-7e79.cachix.org"
  ];
  trusted-public-keys = [
    "linux-ms-7e79.cachix.org-1:Hiw1TafR4Iz0jms+KoR4KadeOWAqqjHxAfsjqsIM7HE="
  ];
};
```

### Flake Configuration

```nix
inputs = {
  linux-ms-7e79.url = "github:xuanyayi/linux-ms-7e79";
};
```

In host configuration:

```nix
boot.kernelPackages = inputs.linux-ms-7e79.legacyPackages.x86_64-linux.kernelPackages;
```

Or via module:

```nix
imports = [
  inputs.linux-ms-7e79.nixosModules.default
];
```

## Maintenance

`kernel/sources.json` pins the official source release, its SHA-256 hash, and an
immutable server-config commit and hash. `kernel/default.nix` builds it with
Nixpkgs; `kernel/config.nix` contains this machine's kernel settings.

```sh
# Check official release/config metadata without changing files.
nix develop --command python3 scripts/update-kernel.py --check

# Download the current pinned source and verify its hashes and official signature.
nix develop --command python3 scripts/update-kernel.py --verify

# Update official kernel sources, then independently update Nixpkgs.
nix develop --command python3 scripts/update-kernel.py
nix flake update nixpkgs

# Validate the updater, boot the kernel in a VM, and build all kernel outputs/module.
nix flake check --print-build-logs
nix build '.#kernel^*' .#nct6687d --no-link --print-build-logs
```

The daily workflow performs these updates automatically. It reads numeric version
assignments from the official server PKGBUILD as data and never executes that
file. New sources must match the official release asset digest and a signature
from a pinned CachyOS signing key before the source manifest is written. Signing
key details and refresh instructions are in [kernel/keys/README.md](kernel/keys/README.md).

Publishing happens only after builds, updater tests and the VM boot test pass.
The VM checks the kernel release, ath12k module loading, nct6687 module metadata,
and OverlayFS mounting. Real Wi-Fi scanning, suspend/resume and sensor readings
still require testing on the physical machine. A failed update leaves the
previous pins on the remote branch; signature failures and replacement of an
existing release archive require investigation.

The CI build cache is restricted to NixOS and this project's Cachix. Cache signatures,
source signatures and VM tests check different properties; none proves that the
official source code is free of malicious changes. Local builds do not switch the
running system or reboot the host.
