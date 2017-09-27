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

prop = "gp3"
filtered = filter(lambda x: x.__contains__(prop), tobii_data)
tobii_pc_data = sorted(filtered, key=operator.itemgetter("ts"))

ts = []
combined = []
for e in tobii_pc_data:
    # apply offset to timestamp
    ts.append(e["ts"] - tobii_offset)
    gazePos = e[prop]
    # No description of the field "l" in the Tobii dev guide
    combined.append([gazePos[0], gazePos[1], gazePos[2], e["s"]])

da = b.create_data_array("gaze position 3D", "nix.tobii.property", data=combined)
da.unit = "mm"
da.label = "positions"
da.description = "The timestamp has been modified by an offset of -" + str(tobii_offset)

dim = da.append_range_dimension(ts)
dim.unit = "us"
dim.label = "timestamp"

dim = da.append_set_dimension()
dim.labels = ["X", "Y", "Z", "error"]

g.data_arrays.append(da.id)

f.close()
