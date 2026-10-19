# Recipe provenance

`default.nix` and `config.nix` adapt the necessary source-preparation and
configuration mapping from Yuhui Xu's (`xddxdd`) `nix-cachyos-kernel`, reviewed at
revision `e61f03b63691ee505bc27274ff1d311a32f64f6c`:

https://github.com/xddxdd/nix-cachyos-kernel/tree/e61f03b63691ee505bc27274ff1d311a32f64f6c

The original project is distributed under GPL version 2; that license is retained
for these two adapted files in `LICENSE`. They were simplified on 2026-10-19 to
support this repository's GCC/server profile with local hardware fixes. General
variant generation, external module overrides, upstream update code and flake
dependencies were removed. Source pins and updates are now maintained here.

This attribution is historical documentation, not a build or update dependency.
Linux, CachyOS sources and Nixpkgs retain their respective licenses.
