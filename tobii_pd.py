#!/usr/bin/env python
import json
import nixio as nix
import operator
import os


def write_tobii_pupil_diameter_eye(b, tobii_data, tobii_offset, eye):
    prop = "pd"
    filtered = filter(lambda y: y["eye"] == eye, filter(lambda x: x.__contains__(prop), tobii_data))
    tobii_pc_data = sorted(filtered, key=operator.itemgetter("ts"))

    ts = []
    combined = []
    for e in tobii_pc_data:
        # apply offset to timestamp
        ts.append(e["ts"] - tobii_offset)
        combined.append([e[prop], e["s"]])

    da = b.create_data_array("pupil diameter " + eye, "nix.tobii.property", data=combined)
    da.unit = "mm"
    da.label = "diameter"
    da.description = "The timestamp has been modified by an offset of -" + str(tobii_offset)

    dim = da.append_range_dimension(ts)
    dim.unit = "us"
    dim.label = "timestamp"

    dim = da.append_set_dimension()
    dim.labels = ["diameter", "error"]

    return da


fp = open(os.path.realpath('livedataPart.json'))
tobii_data = [json.loads(e) for e in fp.readlines()]

tobii_offset = 12

f = nix.File.open("bla.nix", nix.FileMode.Overwrite)
b = f.create_block("stuff", "nix.recording.session")
g = b.create_group("tobii data", "nix.tobii")

da_left = write_tobii_pupil_diameter_eye(b, tobii_data, tobii_offset, "left")
g.data_arrays.append(da_left.id)

da_right = write_tobii_pupil_diameter_eye(b, tobii_data, tobii_offset, "right")
g.data_arrays.append(da_right.id)

f.close()
