{
  perSystem =
    { pkgs, self', ... }:
    {
      checks.e2e-test = pkgs.testers.runNixOSTest {
        name = "e2e-test";
        _module.args.self' = self';
        imports = [ ./e2e-test.nix ];
      };
      checks.e2e-test-dynamic-user = pkgs.testers.runNixOSTest {
        name = "e2e-test-dynamic-user";
        _module.args.self' = self';
        imports = [ ./e2e-test.nix ];
        nodes.machine.systemd.services.counter.serviceConfig.DynamicUser = true;
      };
    };
}
