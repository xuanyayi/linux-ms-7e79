# linux-ms-7e79

Custom Linux kernel builds for MSI MS-7E79 (MPG B850I EDGE TI WIFI).

Based on CachyOS server kernel, with hardware-specific fixes used by this system.

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
