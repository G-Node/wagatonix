NIX converter EEG/TOBII data

$python converter_modasai_gnode.py 20170927_demodata3.mat -m meta-data.txt -t livedata_20170927_demodata3.json

# Validate NIX file
Windows only:
nix-tools.exe validate [filename.nix]

# Validate NIX file via Matlab

f = nix.File.open(‘[filename]’, nix.FileMode.ReadOnly)
f.validate()

