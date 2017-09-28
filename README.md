# NIX importer of g.tec EEG/TOBII data

The script `converter_modasai_gnode.py` is used to import recorded g.tec EEG data
with recorded TOBII eyetracker data into the [NIX data format](https://github.com/G-Node/nix), align the respective
data sets using the TOBII sync signal and tagging regions of interest in all
recorded data sets.

The script has been successfully tested with python2 (v2.7.13) and python3 (v3.6.2).

If you find any bugs or have any feature request, please do not hesitate to create
any issue on the [github repository](https://github.com/G-Node/wagatonix).

## Usage

        $ python converter_modasai_gnode.py [eeg.mat file] -m [metadata file] -t [TOBII json file]

e.g.

        $ python converter_modasai_gnode.py 20170927_demodata3.mat -m meta-data.txt -t livedata_20170927_demodata3.json

To display all commandline options

        $ python converter_modasai_gnode.py -h

The current version requires at least one Matlab file containing g.tec EEG recordings,
a metadata textfile and the livedata.json file of the TOBII eyetracker device.

PLEASE NOTE: If the folder contains more than one Matlab file, with the current file version,
the contents of all Matlab files will be concatenated.

Therefore make sure, that the folder the script is run in contains just the data
of exactly one experiment.


## Validate a created NIX file
To make ensure that the dimensionality of the created DataArrays, Tags and MultiTags 
is correct, NIX files can be validated.

- using Windows, the `nix-tools.exe` file found in `tools` can be used to validate a nix file.

        nix-tools.exe validate [filename.nix]

- using the NIX [Matlab bindings](https://github.com/G-Node/nix-mx)

        f = nix.File.open(‘[filename]’, nix.FileMode.ReadOnly)
        f.validate()

The script `converter_modasai_gnode.py` is based on the `converter_modasai.py` script by Yoshiyuki Asai.

## Use and explore NIX files

NIX files are hdf5 files can be easily accessed using [nixpy](https://github.com/G-Node/nixpy) (Python) 
or [nix-mx](https://github.com/G-Node/nix-mx) (Matlab) 
or by using the [NixView](http://bendalab.github.io/NixView/) toolbox.
