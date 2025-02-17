# install_windows.ps1

# Ensure PowerShell is running with administrative privileges
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator"))
{
    Write-Warning "You do not have Administrator rights to run this script. Please re-run this script as an Administrator."
    exit
}

# Update pip and install pyinstaller
Write-Output "Updating pip..."
python -m pip install --upgrade pip

Write-Output "Installing pyinstaller..."
pip install pyinstaller

# Navigate to the directory containing the main script
cd ..\src

# Use pyinstaller to create an executable
Write-Output "Creating executable using pyinstaller..."
pyinstaller --onefile Porn_Fetch_CLI.py  # Update this line with the correct script name

# Check if the executable was created successfully
if (Test-Path -Path "..\dist\Porn_Fetch_CLI.exe") {  # Update this line with the correct executable name
    Write-Output "Executable was created successfully."
} else {
    Write-Output "Failed to create the executable."
}
