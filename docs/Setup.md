# Installation

## Requirements

- Windows
- Python 3.11 available through the Windows Python Launcher (`py`)
- An internet connection for dependency and model downloads

## Install

1. Extract the project archive to a folder you can write to.
2. Open PowerShell or Command Prompt in that folder.
3. Run:

   ```powershell
   py -3.11 installer.py
   ```

4. Choose automatic setup or run the installation steps individually.

The installer creates the project's `venv`, installs Python dependencies,
downloads configured models, prepares the game files, and creates desktop
shortcuts. The project does not require `.cmd` or batch launcher files.

## Launch

Use the **NMS Dynamic Suit Voice** desktop shortcut to open the Qt control deck.
Select **ENGAGE AI CORE** to start the watcher. Closing the window minimizes it
to the system tray; use **Show Control Deck** to reopen it, or **Close everything
completely** to stop the watcher and exit.

## Update

For ZIP updates, back up configuration files, extract the new archive over the
installation, then run `py -3.11 installer.py` from the project folder again.
For Git-based updates, use the System > Updates panel after converting the
installation to a tracked repository.
