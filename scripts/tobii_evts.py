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

prop = "evts"
filtered = filter(lambda x: x.__contains__(prop), tobii_data)
tobii_pc_data = sorted(filtered, key=operator.itemgetter("ts"))

ts = []
combined = []
for e in tobii_pc_data:
    # apply offset to timestamp
    ts.append(e["ts"] - tobii_offset)
    combined.append([e[prop], e["s"]])

if len(combined) > 0:
    da = b.create_data_array("evts", "nix.tobii.property", data=combined)
    da.unit = "us"
    da.label = "eye video timestamp"
    da.description = "The timestamp has been modified by an offset of -" + str(tobii_offset)

    dim = da.append_range_dimension(ts)
    dim.unit = "us"
    dim.label = "timestamp"

    dim = da.append_set_dimension()
    dim.labels = ["eye video timestamp", "error"]

    g.data_arrays.append(da.id)

f.close()
