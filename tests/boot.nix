{ pkgs, kernelPackages }:
pkgs.testers.runNixOSTest {
  name = "ms-7e79-kernel-boot";
  nodes.machine = {
    boot.kernelPackages = kernelPackages;
    boot.extraModulePackages = [ kernelPackages.nct6687d ];
    virtualisation.memorySize = 1536;
  };
  testScript = ''
    machine.start()
    machine.wait_for_unit("multi-user.target")
    machine.succeed("uname -r | grep -Fx '${kernelPackages.kernel.modDirVersion}'")
    machine.succeed("modprobe ath12k")
    machine.succeed("modinfo nct6687 | grep -F '${kernelPackages.kernel.modDirVersion}'")
    machine.succeed("mkdir -p /tmp/overlay/{lower,upper,work,merged}")
    machine.succeed("mount -t overlay overlay -o lowerdir=/tmp/overlay/lower,upperdir=/tmp/overlay/upper,workdir=/tmp/overlay/work /tmp/overlay/merged")
  '';
}
