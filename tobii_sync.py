#!/usr/bin/env python
import json
import nixio as nix
import operator
import os


fp = open(os.path.realpath('livedataPart.json'))
tobii_data = [json.loads(e) for e in fp.readlines()]

tobii_offset = 12

f = nix.File.open("bla.nix", nix.FileMode.Overwrite)
b = f.create_block("stuff", "nix.recording.session")
g = b.create_group("tobii data", "nix.tobii")

prop = "dir"
filtered = filter(lambda x: x.__contains__(prop), tobii_data)
tobii_pc_data = sorted(filtered, key=operator.itemgetter("ts"))

ts = []
combined = []
for e in tobii_pc_data:
    # apply offset to timestamp
    ts.append(e["ts"] - tobii_offset)
    sig_dir = 0
    if e[prop] == "in":
        sig_dir = 1
    combined.append([sig_dir, e["sig"], e["s"]])

da = b.create_data_array("sync port", "nix.tobii.property", data=combined)
da.label = "sync port"

ts_desc = "The timestamp has been modified by an offset of -" + str(tobii_offset)
da.description = ts_desc + "; direction 0=out, 1=in"

dim = da.append_range_dimension(ts)
dim.unit = "us"
dim.label = "timestamp"

dim = da.append_set_dimension()
dim.labels = ["direction", "signal", "error"]

g.data_arrays.append(da.id)

f.close()
