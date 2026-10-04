{
  description = "Linux kernel builds and hardware fixes for MSI MS-7E79 (MPG B850I EDGE TI WIFI)";

  inputs = {
    nixpkgs.follows = "cachyos-upstream/nixpkgs";
    cachyos-upstream.url = "github:xddxdd/nix-cachyos-kernel";
  };

  nixConfig = {
    extra-substituters = [
      "https://linux-ms-7e79.cachix.org"
    ];
    extra-trusted-public-keys = [
      "linux-ms-7e79.cachix.org-1:Hiw1TafR4Iz0jms+KoR4KadeOWAqqjHxAfsjqsIM7HE="
    ];
  };

  outputs =
    {
      self,
      nixpkgs,
      cachyos-upstream,
    }:
    let
      supportedSystems = [ "x86_64-linux" ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
    in
    {
      legacyPackages = forAllSystems (
        system:
        let
          pkgs = import nixpkgs {
            inherit system;
            config.allowUnfree = true;
          };
          inherit (pkgs) lib;

          # Base CachyOS server kernel from upstream
          baseServerKernel = cachyos-upstream.legacyPackages.${system}.linux-cachyos-server;

          # Custom server kernel configuration for MS-7E79:
          # - EEVDF scheduler (server default)
          # - PREEMPT_LAZY with dynamic preemption
          # - 300 Hz timer frequency
          # - NO_HZ_FULL tickless
          # - GCC build (no LLVM LTO)
          # - MS-7E79 hardware fixes:
          #   1. WCN7850 dynamic user regulatory hints
          #   2. WCN7850 5 GHz channel scan frequency range fix
          patchedKernel = baseServerKernel.override {
            preemptType = "lazy";
            tickrate = "full";
            structuredExtraConfig = {
              ATH_REG_DYNAMIC_USER_REG_HINTS = lib.kernel.yes;
            };
            patches = [
              ./patches/ath12k-wcn7850-5ghz-scan.patch
            ];
          };

          kernelPackages = pkgs.linuxKernel.packagesFor patchedKernel;
        in
        {
          inherit patchedKernel kernelPackages;
        }
      );

      packages = forAllSystems (system: {
        kernel = self.legacyPackages.${system}.patchedKernel;
        default = self.legacyPackages.${system}.patchedKernel;
        nct6687d = self.legacyPackages.${system}.kernelPackages.nct6687d;
      });

      overlays.default = final: prev: {
        linuxPackages_ms_7e79 =
          self.legacyPackages.${final.stdenv.hostPlatform.system}.kernelPackages;
      };

      nixosModules.default =
        { pkgs, ... }:
        {
          boot.kernelPackages =
            self.legacyPackages.${pkgs.stdenv.hostPlatform.system}.kernelPackages;
        };
    };
}
