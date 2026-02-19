{
  description = "Scraper RPA — ambiente de desenvolvimento com Python 3.12";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python312;

        pythonEnv = python.withPackages (ps: with ps; [
          pip
          virtualenv
        ]);
      in
      {
        devShells.default = pkgs.mkShell {
          name = "scraper-rpa";

          buildInputs = [
            pythonEnv
            pkgs.postgresql_15   # cliente psql para debug
            pkgs.docker
            pkgs.docker-compose
            pkgs.google-cloud-sdk  # gcloud para GCR
            pkgs.chromedriver      # para Selenium
            pkgs.chromium
          ];

          shellHook = ''
            # Cria e ativa virtualenv se não existir
            if [ ! -d .venv ]; then
              python -m venv .venv
              echo "Virtualenv criado em .venv"
            fi
            source .venv/bin/activate

            # Instala dependências de dev se necessário
            if [ ! -f .venv/.deps-installed ]; then
              pip install -r requirements-dev.txt
              touch .venv/.deps-installed
            fi

            echo ""
            echo "  Ambiente Scraper RPA carregado!"
            echo "  Python: $(python --version)"
            echo ""
            echo "  Comandos úteis:"
            echo "    docker-compose up       → subir todos os serviços"
            echo "    pytest tests/unit/      → testes unitários"
            echo "    pytest tests/integration/ → testes de integração"
            echo "    ruff check .            → lint"
            echo "    black .                 → formatação"
            echo ""
          '';

          # Variáveis de ambiente para desenvolvimento local
          POSTGRES_HOST = "localhost";
          POSTGRES_PORT = "5432";
          POSTGRES_USER = "postgres";
          POSTGRES_PASSWORD = "postgres";
          POSTGRES_DB = "scraper_db";
          RABBITMQ_HOST = "localhost";
          RABBITMQ_USER = "guest";
          RABBITMQ_PASSWORD = "guest";
          SELENIUM_HEADLESS = "true";
        };
      }
    );
}
