{
  description = "CreditRadar: personal credit intelligence for the Brazilian credit market";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    { nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          name = "credit-radar";

          # Nix provides interpreters and system-level tooling only.
          # Project dependencies stay with each ecosystem's own manager:
          #   uv    -> Python packages
          #   pnpm  -> frontend packages
          #   docker -> service execution
          # Replacing those with Nix would mean maintaining a third
          # dependency graph that neither ecosystem's tooling understands.
          packages = with pkgs; [
            # Backend
            python313
            uv

            # Frontend
            nodejs_22
            pnpm

            # Database client, for inspecting the containerized instance
            postgresql_17

            # Containers
            docker-client
            docker-compose

            # Utilities
            git
            jq
            curl
          ];

          shellHook = ''
            # uv builds its own virtualenv; keep it from trying to manage
            # the interpreter itself.
            export UV_PYTHON_DOWNLOADS=never
            export UV_PYTHON="${pkgs.python313}/bin/python3.13"

            echo "CreditRadar development shell"
            echo "  python $(python3 --version 2>&1 | cut -d' ' -f2)  uv $(uv --version | cut -d' ' -f2)"
            echo "  node $(node --version)  pnpm $(pnpm --version)"
            echo
            echo "  backend:   cd backend  && uv sync && uv run pytest"
            echo "  frontend:  cd frontend && pnpm install && pnpm dev"
            echo "  database:  docker compose up -d postgres"
          '';
        };
      }
    );
}
