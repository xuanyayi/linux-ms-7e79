{
  description = "Linux kernel builds and hardware fixes for MSI MS-7E79 (MPG B850I EDGE TI WIFI)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable-small";
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
          patchedKernel = import ./kernel {
            inherit (pkgs)
              lib
              buildLinux
              fetchurl
              applyPatches
              kernelPatches
              ;
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

      devShells = forAllSystems (system: {
        default = nixpkgs.legacyPackages.${system}.mkShellNoCC {
          packages = with nixpkgs.legacyPackages.${system}; [
            python3
            gnupg
            cachix
          ];
        };
      });

      formatter = forAllSystems (system: nixpkgs.legacyPackages.${system}.nixfmt-tree);

      checks = forAllSystems (system: {
        boot = import ./tests/boot.nix {
          pkgs = nixpkgs.legacyPackages.${system};
          kernelPackages = self.legacyPackages.${system}.kernelPackages;
        };
        updater =
          nixpkgs.legacyPackages.${system}.runCommand "kernel-updater-tests"
            {
              nativeBuildInputs = [ nixpkgs.legacyPackages.${system}.python3 ];
              UPDATER_SCRIPT = ./scripts/update-kernel.py;
            }
            ''
              export PYTHONDONTWRITEBYTECODE=1
              python3 -m unittest discover -s ${./tests} -p 'test_*.py' -v
              touch "$out"
            '';
      });

      overlays.default = final: prev: {
        linuxPackages_ms_7e79 = self.legacyPackages.${final.stdenv.hostPlatform.system}.kernelPackages;
      };

      nixosModules.default =
        { pkgs, ... }:
        {
          boot.kernelPackages = self.legacyPackages.${pkgs.stdenv.hostPlatform.system}.kernelPackages;
        };
    };
}
