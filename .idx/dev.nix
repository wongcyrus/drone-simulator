# To learn more about how to use Nix to configure your environment
# see: https://firebase.google.com/docs/studio/customize-workspace
{ pkgs, ... }: {
  # Which nixpkgs channel to use.
  channel = "stable-24.05"; # or "unstable"

  # Use https://search.nixos.org/packages to find packages
  packages = [
    # pkgs.go
    # pkgs.python311
    pkgs.python312
    # pkgs.nodejs_20
    # pkgs.nodePackages.nodemon
  ];

  # Sets environment variables in the workspace
  # environment variables
  env = {
    VENV_DIR = ".venv";
  };
  idx = {
    # Search for the extensions you want on https://open-vsx.org/ and use "publisher.id"
    extensions = [
      "ms-python.python"
      "ms-python.vscode-pylance"
      "ms-python.black-formatter"
      "ms-python.flake8"
      "ms-python.pylint"
      "ms-python.isort"
      "ms-toolsai.jupyter"
      "esbenp.prettier-vscode"
      "freakypie.code-python-isort"
    ];

    # Enable previews
    previews = {
      enable = true;
      previews = {
        # web = {
        #   # Example: run "npm run dev" with PORT set to IDX's defined port for previews,
        #   # and show it in IDX's web preview panel
        #   command = ["npm" "run" "dev"];
        #   manager = "web";
        #   env = {
        #     # Environment variables to set for your server
        #     PORT = "$PORT";
        #   };
        # };
        web = {
          # cwd = "subfolder"
          command = [
            "bash"
            "-c"
            ''
            # activate the virtual environment
            source $VENV_DIR/bin/activate
            
            # run app in hot reload mode on a port provided by IDX
            python -m backend.server
            ''
          ];
          env = { PORT = "$PORT"; };
          manager = "web";
        };

      };
    };

    # Workspace lifecycle hooks
    workspace = {
      # Runs when a workspace is first created
      onCreate = {
        # create a python virtual environment
        create-venv = ''
          python -m venv $VENV_DIR
          # activate virtual env and install requirements
          source $VENV_DIR/bin/activate
          pip install -r requirements.txt
        '';

        # Open editors for the following files by default, if they exist:
        default.openFiles = [ "README.md" ];
      };

      onStart = {
        # check the existence of the venv and create if non-existent
        check-venv-existence = ''
          if [ ! -d $VENV_DIR ]; then
            echo "Virtual environment not found. Creating one..."
            python -m venv $VENV_DIR
          fi
          # activate virtual env and install requirements
          source $VENV_DIR/bin/activate
          pip install -r requirements.txt
        '';
        #web-backend = "source $VENV_DIR/bin/activate && python -m backend.server";
        mock-drone1 = "source $VENV_DIR/bin/activate && sleep 5 && python -m mock_drone.mock_drone --drone-id drone_1 --port 8889";
        mock-drone2 = "source $VENV_DIR/bin/activate && sleep 5 && python -m mock_drone.mock_drone --drone-id drone_2 --port 8890";
      };
      # Runs when the workspace is (re)started
    };

  };
  services.docker = {
    enable = true;
  };
}
