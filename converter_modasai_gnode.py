#!/usr/bin/env python
from __future__ import print_function
import argparse
import csv
import glob
import json
import nixio as nix
import numpy as np
import operator
import os
import scipy.io as scio
import sys


def write_eeg_hardware_metadata(block, group):
    src = block.create_source("eeg setup", "eeg.channel_group")
    group.sources.append(src)
    block.metadata["hardware"] = nix.S("recording hardware")
    block.metadata["hardware"]["eeg system"] = nix.S("hardware.eeg")
    return block.metadata["hardware"]["eeg system"]


def write_channel_metadata(section, name, gain=100):
    section[name] = nix.S("eeg_channel")
    section[name]["gain"] = gain
    return section[name]


def write_session_metadata(nixfile, block, metadatafile):
    print("INFO: Writing metadata from '%s' to NIX" % metadatafile)
    md_sec = nixfile.create_section(block.name, "recording")
    # rec_sec["experimenter"] = "John Doe"
    # rec_sec["startDate"] = "-".join([block.name[:4], block.name[4:6], block.name[6:8]])
    block.metadata = md_sec
    msecs = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    msecs[0] = md_sec

    if sys.version_info[0] < 3:
        mdf = open(metadatafile, 'rb')
    else:
        mdf = open(metadatafile)

    prevcnt = 0
    for mdatrow in csv.reader(mdf):
        # print("---{0}".format(mdatrow))
        for (cnt, mdat) in enumerate(mdatrow):
            if mdat != '':
                # print("***{0}".format(mdat))
                if cnt > prevcnt + 1:
                    break
                
                if len(mdatrow) > cnt + 1:
                    # print("{0}".format(len(mdatrow)))
                    # print("{0} {1} {2}".format(cnt, mdatrow, mdat))
                    msecs[cnt][mdat] = mdatrow[cnt + 1]
                    break
                else:
                    msecs[cnt][mdat] = nix.S(mdat)
                    msecs[cnt + 1] = msecs[cnt][mdat]
                    prevcnt = cnt
                    break


def write_subject_metadata(recording_session, name, species="homo sapiens"):
    recording_session["subject"] = nix.S("subject")
    recording_session["subject"]["name"] = name
    recording_session["subject"]["species"] = species
    recording_session["subject"]["age"] = 54


def write_channel_data(block, data, time, sr, offset):
    group = block.create_group("eeg data", "nix.eeg.channels")
    hw = write_eeg_hardware_metadata(block, group)

    # with the current implementation, we should always use range dimension,
    # since the time requires to be modified by an offset for alignment
    # with other data.

    # dt = np.mean(np.diff(time))
    # diff = 1./dt - sr
    # use_range = diff > np.finfo(np.float32).eps

    # if use_range:
    #     print("sampling rate does not match timestamps using range dimension (need more space!)",
    #          file=sys.stderr)

    nchan = data.shape[0]

    for ch in range(nchan):
        chdata = data[ch, :]
        da = block.create_data_array("channel %d" % (ch + 1), "nix.eeg.channeldata",
                                     data=chdata.astype(np.double))
        da.unit = "uV"
        da.label = "voltage"
        da.description = "Time"
        da.description = "The time dimension has been modified by -" + str(offset)

        # if use_range:
        #     dim = da.append_range_dimension(time)
        # else:
        #     dim = da.append_sampled_dimension(dt)

        dim = da.append_range_dimension(time)
        dim.unit = "s"
        dim.label = "time"
        sec = write_channel_metadata(hw, "channel %d" % (ch + 1), 100+ch)
        da.metadata = sec
        group.data_arrays.append(da)

    return group


def save_events(block, trigger, group_eeg, group_tobii):
    states = trigger[np.nonzero(np.diff(trigger))]
    indices = np.nonzero(np.diff(trigger))
    times = indices[0].astype(np.double) / 512
    corners = times[(states == 8) | (states == 10)]
    exp_start = times[(states == 4) | (states == 6)]

    handle_multi_tags = []

    # handle corner position multi_tag, do not create empty data arrays
    if len(corners) < 1:
        print("WARNING/TAGS: No corner positions found, MultiTag not created.")
    else:
        corner_positions = block.create_data_array("corner_times", "nix.timestamps", data=corners)
        corner_positions.label = "time"
        corner_positions.unit = "s"
        corner_positions.append_alias_range_dimension()
        corner_events = block.create_multi_tag("corners", "nix.eeg.event", corner_positions)

        handle_multi_tags.append(corner_events)

    # handle experiment start position multi_tag
    if len(exp_start) < 1:
        print("WARNING/TAGS: No experiment start positions found, MultiTag not created.")
    else:
        exp_positions = block.create_data_array("experiment times", "nix.timestamps", data=exp_start)
        exp_positions.label = "time"
        exp_positions.unit = "s"
        exp_positions.append_alias_range_dimension()

        extents = np.ones(len(exp_start))
        if len(extents) > 1:
            extents[-1] = 100.
        else:
            extents = [100]
        exp_extents = block.create_data_array("experiment durations", "nix.extents", data=extents)
        exp_extents.label = "time"
        exp_extents.unit = "s"
        exp_extents.append_alias_range_dimension()

        exp_starts = block.create_multi_tag("experiment starts", "nix.eeg.event", exp_positions)
        exp_starts.extents = exp_extents

        handle_multi_tags.append(exp_starts)

    for mt in handle_multi_tags:
        print("INFO/TAGS: Applying MultiTag '%s'." % mt.name)
        mt.references.extend(group_eeg.data_arrays)
        mt.references.extend(group_tobii.data_arrays)


def write_trigger_signal(block, trigger, time, da_group, offset):
    trigger_da = block.create_data_array("trigger signal", "nix.eeg.trigger",
                                         data=trigger.astype(np.double))
    trigger_da.label = "voltage"
    trigger_da.unit = "mV"
    trigger_da.description = "The time dimension has been modified by -" + str(offset)

    dim = trigger_da.append_sampled_dimension(np.mean(np.diff(time)))
    dim.unit = "s"
    dim.label = "time"

    tag = block.create_tag("trigger signal", "nix.eeg.trigger", [0.])
    tag.extent = [time[-1]]  # list of extents, one for each dimension
    tag.units = ["s"]  # list of units, need one entry for each dimension of the data
    for da in da_group.data_arrays:
        tag.references.append(da)
    tag.create_feature(trigger_da, nix.LinkType.Tagged)


def determine_offsets(time, trigger, tobii_data):
    """
    Determines the offsets (ate the first trigger) in the eeg and in the tobii signal
    assumes that the first 6 [0:5] trigger signals in the tobii  are pre sync pulses
     and takes the first sync pulse as reference.
     return time offset off the first sync pulse in the eeg (in second) and the corresponing point in the tobii (us)
    :param time: time vector of the eeg signal
    :param trigger: trigger signals in teh eeg
    :param tobii_data: json formatted signal form the tobii
    :return:
    """
    trigger_on_erg = np.logical_and(np.diff(trigger) > 1, np.diff(trigger) < 5)
    # trigger_off_erg = np.logical_and(np.diff(trigger) < -1, np.diff(trigger) > -5)
    sync_trigger_tobii = list(filter(lambda y: y["dir"] == "out", filter(lambda x: x.__contains__("dir"), tobii_data)))
    sync_trigger_eeg = time[np.where(trigger_on_erg)[0][3]]
    # sync pulse must comes 10s after first pulse
    return sync_trigger_eeg, sync_trigger_tobii[0]["ts"] + 10 * 10 ** 6


def convert(time, trigger, data, parts, sr, tobii_data, metadatafile, eeg_offset, tobii_offset):
    f = nix.File.open(parts[0] + ".nix", nix.FileMode.Overwrite)

    # handle eeg data
    b = f.create_block(parts[0], "nix.recording.session")

    write_session_metadata(f, b, metadatafile)

    group_eeg = write_channel_data(b, data, time, sr, eeg_offset)
    write_trigger_signal(b, trigger, time, group_eeg, eeg_offset)

    # handle tobii data
    group_tobii = write_tobii_data(b, tobii_data, tobii_offset)

    # apply multi_tags
    save_events(b, trigger, group_eeg, group_tobii)

    f.close()


def write_tobii_data(b, tobii_data, tobii_offset):
    group = b.create_group("tobii data", "nix.tobii")

    write_tobii_pupil_center(b, group, tobii_data, tobii_offset, "left")
    write_tobii_pupil_center(b, group, tobii_data, tobii_offset, "right")

    write_tobii_pupil_diameter(b, group, tobii_data, tobii_offset, "left")
    write_tobii_pupil_diameter(b, group, tobii_data, tobii_offset, "right")

    write_tobii_gaze_dir(b, group, tobii_data, tobii_offset, "left")
    write_tobii_gaze_dir(b, group, tobii_data, tobii_offset, "right")

    write_tobii_gaze_pos(b, group, tobii_data, tobii_offset)

    write_tobii_gaze_pos_3d(b, group, tobii_data, tobii_offset)

    write_tobii_gyroscope(b, group, tobii_data, tobii_offset)

    write_tobii_accelerometer(b, group, tobii_data, tobii_offset)

    write_tobii_pipe_ts(b, group, tobii_data, tobii_offset)

    write_tobii_video_ts(b, group, tobii_data, tobii_offset)

    write_tobii_eye_video_ts(b, group, tobii_data, tobii_offset)

    write_tobii_sync_port(b, group, tobii_data, tobii_offset)

    return group


def create_range_data_array(b, name, nix_type, desc, data, label, unit, range_data, range_label, range_unit):
    da = b.create_data_array(name + " " + label, nix_type, data=data)
    da.description = desc
    da.label = label
    if unit:
        da.unit = unit
    dim = da.append_range_dimension(range_data)
    dim.label = range_label
    if range_unit:
        dim.unit = range_unit

    return da


def write_tobii_sync_port(b, group, tobii_data, tobii_offset):
    prop = "dir"
    filtered = filter(lambda x: x.__contains__(prop), tobii_data)
    tobii_pc_data = sorted(filtered, key=operator.itemgetter("ts"))

    ts = []
    direction = []
    sig = []
    err = []
    for e in tobii_pc_data:
        # apply offset to timestamp
        ts.append(e["ts"] - tobii_offset)
        sig_dir = 0
        if e[prop] == "in":
            sig_dir = 1
        direction.append(sig_dir)
        sig.append(e["sig"])
        err.append(e["s"])

    if len(err) < 1:
        print("INFO/TOBII: no '%s' data found" % prop)
    else:
        desc = "The timestamp has been modified by an offset of -" + str(tobii_offset)
        desc = desc + "; direction 0=out, 1=in"

        nix_type = "nix.tobii.property." + prop
        name = "sync port"

        da_x = create_range_data_array(b, name, nix_type, desc, direction, "direction", "",
                                       ts, "timestamp", "us")
        da_y = create_range_data_array(b, name, nix_type, desc, sig, "signal", "",
                                       ts, "timestamp", "us")
        da_e = create_range_data_array(b, name, nix_type, desc, err, "error", "",
                                       ts, "timestamp", "us")

        for d in [da_x, da_y, da_e]:
            group.data_arrays.append(d.id)


def write_tobii_eye_video_ts(b, group, tobii_data, tobii_offset):
    prop = "evts"
    filtered = filter(lambda x: x.__contains__(prop), tobii_data)
    tobii_pc_data = sorted(filtered, key=operator.itemgetter("ts"))

    ts = []
    evts = []
    err = []
    for e in tobii_pc_data:
        # apply offset to timestamp
        ts.append(e["ts"] - tobii_offset)
        evts.append(e[prop])
        err.append(e["s"])

    if len(err) < 1:
        print("INFO/TOBII: no '%s' data found" % prop)
    else:
        desc = "The timestamp has been modified by an offset of -" + str(tobii_offset)
        nix_type = "nix.tobii.property." + prop
        name = "evts"

        da_x = create_range_data_array(b, name, nix_type, desc, evts, "eye video timestamp", "us",
                                       ts, "timestamp", "us")
        da_e = create_range_data_array(b, name, nix_type, desc, err, "error", "",
                                       ts, "timestamp", "us")

        for d in [da_x, da_e]:
            group.data_arrays.append(d.id)


def write_tobii_video_ts(b, group, tobii_data, tobii_offset):
    prop = "vts"
    filtered = filter(lambda x: x.__contains__(prop), tobii_data)
    tobii_pc_data = sorted(filtered, key=operator.itemgetter("ts"))

    ts = []
    vts = []
    err = []
    for e in tobii_pc_data:
        # apply offset to timestamp
        ts.append(e["ts"] - tobii_offset)
        vts.append(e[prop])
        err.append(e["s"])

    if len(err) < 1:
        print("INFO/TOBII: no '%s' data found" % prop)
    else:
        desc = "The timestamp has been modified by an offset of -" + str(tobii_offset)
        nix_type = "nix.tobii.property." + prop
        name = "vts"

        da_x = create_range_data_array(b, name, nix_type, desc, vts, "video timestamp", "us",
                                       ts, "timestamp", "us")
        da_e = create_range_data_array(b, name, nix_type, desc, err, "error", "",
                                       ts, "timestamp", "us")

        for d in [da_x, da_e]:
            group.data_arrays.append(d.id)


def write_tobii_pipe_ts(b, group, tobii_data, tobii_offset):
    prop = "pts"
    filtered = filter(lambda x: x.__contains__(prop), tobii_data)
    tobii_pc_data = sorted(filtered, key=operator.itemgetter("ts"))

    ts = []
    pts = []
    pv = []
    err = []
    for e in tobii_pc_data:
        # apply offset to timestamp
        ts.append(e["ts"] - tobii_offset)
        pts.append(e[prop])
        pv.append(e["pv"])
        err.append(e["s"])

    if len(err) < 1:
        print("INFO/TOBII: no '%s' data found" % prop)
    else:
        desc = "The timestamp has been modified by an offset of -" + str(tobii_offset)
        nix_type = "nix.tobii.property." + prop
        name = "pts"

        da_x = create_range_data_array(b, name, nix_type, desc, pts, "pipe timestamp", "us",
                                       ts, "timestamp", "us")
        da_y = create_range_data_array(b, name, nix_type, desc, pv, "pipe version", "",
                                       ts, "timestamp", "us")
        da_e = create_range_data_array(b, name, nix_type, desc, err, "error", "",
                                       ts, "timestamp", "us")

        for d in [da_x, da_y, da_e]:
            group.data_arrays.append(d.id)


def write_tobii_accelerometer(b, group, tobii_data, tobii_offset):
    prop = "ac"
    filtered = filter(lambda x: x.__contains__(prop), tobii_data)
    tobii_pc_data = sorted(filtered, key=operator.itemgetter("ts"))

    ts = []
    coord = []
    err = []
    for e in tobii_pc_data:
        # apply offset to timestamp
        ts.append(e["ts"] - tobii_offset)
        coord.append(e[prop])
        err.append(e["s"])

    if len(err) < 1:
        print("INFO/TOBII: no '%s' data found" % prop)
    else:
        coord = np.transpose(coord)

        desc = "The timestamp has been modified by an offset of -" + str(tobii_offset)
        nix_type = "nix.tobii.property." + prop
        name = "MEMS accelerometer"

        da_x = create_range_data_array(b, name, nix_type, desc, coord[0], "movementX", "m/s^2",
                                       ts, "timestamp", "us")
        da_y = create_range_data_array(b, name, nix_type, desc, coord[1], "movementY", "m/s^2",
                                       ts, "timestamp", "us")
        da_z = create_range_data_array(b, name, nix_type, desc, coord[2], "movementZ", "m/s^2",
                                       ts, "timestamp", "us")
        da_e = create_range_data_array(b, name, nix_type, desc, err, "error", "",
                                       ts, "timestamp", "us")

        for d in [da_x, da_y, da_z, da_e]:
            group.data_arrays.append(d.id)


def write_tobii_gyroscope(b, group, tobii_data, tobii_offset):
    prop = "gy"
    filtered = filter(lambda x: x.__contains__(prop), tobii_data)
    tobii_pc_data = sorted(filtered, key=operator.itemgetter("ts"))

    ts = []
    coord = []
    err = []
    for e in tobii_pc_data:
        # apply offset to timestamp
        ts.append(e["ts"] - tobii_offset)
        coord.append(e[prop])
        err.append(e["s"])

    if len(err) < 1:
        print("INFO/TOBII: no '%s' data found" % prop)
    else:
        coord = np.transpose(coord)

        desc = "The timestamp has been modified by an offset of -" + str(tobii_offset)
        nix_type = "nix.tobii.property." + prop
        name = "MEMS gyroscope"

        # TODO conversion from deg/s to nix supported rad/s
        # da.unit = "rad/s"
        da_x = create_range_data_array(b, name, nix_type, desc, coord[0], "rotationX", "",
                                       ts, "timestamp", "us")
        da_y = create_range_data_array(b, name, nix_type, desc, coord[1], "rotationY", "",
                                       ts, "timestamp", "us")
        da_z = create_range_data_array(b, name, nix_type, desc, coord[2], "rotationZ", "",
                                       ts, "timestamp", "us")
        da_e = create_range_data_array(b, name, nix_type, desc, err, "error", "",
                                       ts, "timestamp", "us")

        for d in [da_x, da_y, da_z, da_e]:
            group.data_arrays.append(d.id)


def write_tobii_gaze_pos_3d(b, group, tobii_data, tobii_offset):
    prop = "gp3"
    filtered = filter(lambda x: x.__contains__(prop), tobii_data)
    tobii_pc_data = sorted(filtered, key=operator.itemgetter("ts"))

    ts = []
    gaze_pos = []
    err = []
    for e in tobii_pc_data:
        # apply offset to timestamp
        ts.append(e["ts"] - tobii_offset)
        gaze_pos.append(e[prop])
        err.append(e["s"])

    if len(err) < 1:
        print("INFO/TOBII: no '%s' data found" % prop)
    else:
        gaze_pos = np.transpose(gaze_pos)

        desc = "The timestamp has been modified by an offset of -" + str(tobii_offset)
        nix_type = "nix.tobii.property." + prop
        name = "gaze position 3D"

        da_x = create_range_data_array(b, name, nix_type, desc, gaze_pos[0], "positionX", "mm",
                                       ts, "timestamp", "us")
        da_y = create_range_data_array(b, name, nix_type, desc, gaze_pos[1], "positionY", "mm",
                                       ts, "timestamp", "us")
        da_z = create_range_data_array(b, name, nix_type, desc, gaze_pos[2], "positionZ", "mm",
                                       ts, "timestamp", "us")
        da_e = create_range_data_array(b, name, nix_type, desc, err, "error", "",
                                       ts, "timestamp", "us")

        for d in [da_x, da_y, da_z, da_e]:
            group.data_arrays.append(d.id)


def write_tobii_gaze_pos(b, group, tobii_data, tobii_offset):
    prop = "gp"
    filtered = filter(lambda x: x.__contains__(prop), tobii_data)
    tobii_pc_data = sorted(filtered, key=operator.itemgetter("ts"))

    ts = []
    gaze_pos = []
    l_var = []
    err = []
    for e in tobii_pc_data:
        # apply offset to timestamp
        ts.append(e["ts"] - tobii_offset)
        gaze_pos.append(e[prop])
        # No description of the field "l" in the Tobii dev guide
        l_var.append(e["l"])
        err.append(e["s"])

    if len(err) < 1:
        print("INFO/TOBII: no '%s' data found" % prop)
    else:
        gaze_pos = np.transpose(gaze_pos)

        desc = "The timestamp has been modified by an offset of -" + str(tobii_offset)
        nix_type = "nix.tobii.property." + prop
        name = "gaze position "

        da_x = create_range_data_array(b, name, nix_type, desc, gaze_pos[0], "X", "",
                                       ts, "timestamp", "us")
        da_y = create_range_data_array(b, name, nix_type, desc, gaze_pos[1], "Y", "",
                                       ts, "timestamp", "us")
        da_l = create_range_data_array(b, name, nix_type, desc, l_var, "l", "",
                                       ts, "timestamp", "us")
        da_e = create_range_data_array(b, name, nix_type, desc, err, "error", "",
                                       ts, "timestamp", "us")

        for d in [da_x, da_y, da_l, da_e]:
            group.data_arrays.append(d.id)


def write_tobii_gaze_dir(b, group, tobii_data, tobii_offset, eye):
    prop = "gd"
    filtered = filter(lambda y: y["eye"] == eye, filter(lambda x: x.__contains__(prop), tobii_data))
    tobii_pc_data = sorted(filtered, key=operator.itemgetter("ts"))

    ts = []
    coord = []
    err = []
    for e in tobii_pc_data:
        # apply offset to timestamp
        ts.append(e["ts"] - tobii_offset)
        coord.append(e[prop])
        err.append(e["s"])

    if len(err) < 1:
        print("INFO/TOBII: no '%s' data found" % prop)
    else:
        coord = np.transpose(coord)

        desc = "The timestamp has been modified by an offset of -" + str(tobii_offset)
        nix_type = "nix.tobii.property." + prop
        name = "gaze direction " + eye

        da_x = create_range_data_array(b, name, nix_type, desc, coord[0], "coordinatesX", "",
                                       ts, "timestamp", "us")
        da_y = create_range_data_array(b, name, nix_type, desc, coord[1], "coordinatesY", "",
                                       ts, "timestamp", "us")
        da_z = create_range_data_array(b, name, nix_type, desc, coord[2], "coordinatesZ", "",
                                       ts, "timestamp", "us")
        da_e = create_range_data_array(b, name, nix_type, desc, err, "error", "",
                                       ts, "timestamp", "us")

        for d in [da_x, da_y, da_z, da_e]:
            group.data_arrays.append(d.id)


def write_tobii_pupil_center(b, group, tobii_data, tobii_offset, eye):
    prop = "pc"
    filtered = filter(lambda y: y["eye"] == eye, filter(lambda x: x.__contains__(prop), tobii_data))
    tobii_pc_data = sorted(filtered, key=operator.itemgetter("ts"))

    ts = []
    coord = []
    err = []
    for e in tobii_pc_data:
        # apply tobii offset to timestamp
        ts.append(e["ts"] - tobii_offset)
        coord.append(e[prop])
        err.append(e["s"])

    if len(err) < 1:
        print("INFO/TOBII: no '%s' data found" % prop)
    else:
        coord = np.transpose(coord)

        desc = "The timestamp has been modified by an offset of -" + str(tobii_offset)
        name = "pupil center " + eye
        nix_type = "nix.tobii.property." + prop

        da_x = create_range_data_array(b, name, nix_type, desc, coord[0], "coordinatesX", "mm",
                                       ts, "timestamp", "us")
        da_y = create_range_data_array(b, name, nix_type, desc, coord[1], "coordinatesY", "mm",
                                       ts, "timestamp", "us")
        da_z = create_range_data_array(b, name, nix_type, desc, coord[2], "coordinatesZ", "mm",
                                       ts, "timestamp", "us")
        da_e = create_range_data_array(b, name, nix_type, desc, err, "error", "",
                                       ts, "timestamp", "us")

        for d in [da_x, da_y, da_z, da_e]:
            group.data_arrays.append(d.id)


def write_tobii_pupil_diameter(b, group, tobii_data, tobii_offset, eye):
    prop = "pd"
    filtered = filter(lambda y: y["eye"] == eye, filter(lambda x: x.__contains__(prop), tobii_data))
    tobii_pc_data = sorted(filtered, key=operator.itemgetter("ts"))

    ts = []
    diameter = []
    err = []
    for e in tobii_pc_data:
        # apply offset to timestamp
        ts.append(e["ts"] - tobii_offset)
        diameter.append(e[prop])
        err.append(e["s"])

    if len(err) < 1:
        print("INFO/TOBII: no '%s' data found" % prop)
    else:
        desc = "The timestamp has been modified by an offset of -" + str(tobii_offset)
        name = "pupil diameter " + eye
        nix_type = "nix.tobii.property." + prop

        da = create_range_data_array(b, name, nix_type, desc, diameter, "pupil diameter", "mm",
                                     ts, "timestamp", "us")
        da_e = create_range_data_array(b, name, nix_type, desc, err, "error", "",
                                       ts, "timestamp", "us")

        for d in [da, da_e]:
            group.data_arrays.append(d.id)


def load_data(filename):
    folder = os.path.dirname(filename)
    full_name = os.path.basename(filename)
    name, ext = os.path.splitext(full_name)
    file_parts = name.split("_")
    pattern = "_".join(file_parts[:-1])
    files = glob.glob(os.path.join(folder, pattern + "*.mat"))
    combined_data = None
    for f in files:
        print("INFO/EEG: Importing file '%s'" % f)
        data = scio.matlab.loadmat(f)
        y = np.squeeze(data["y"])
        if combined_data is None:
            combined_data = y
        else:
            last_time = combined_data[0, -1]
            dt = np.mean(np.diff(combined_data[0, :]))
            y[0, :] = y[0, :] + last_time + dt
            combined_data = np.hstack((combined_data, y))
    sr_key = [x for x in data.keys() if x.startswith('SR')][0]
    sr = data[sr_key][0][0]
    time = combined_data[0, :]
    trigger = combined_data[-1, :]
    data_eeg = combined_data[1:-1, :]  # fixed offset bug -2 -> -1
    return time, trigger, data_eeg, file_parts, sr


def load_tobii_data(filename):
    """
    load data from tobii json file into json python object
    :param filename:
    :return: json python object
    """
    print("INFO/TOBII: Importing file '%s'" % filename)
    fp = open(filename)
    return [json.loads(e) for e in fp.readlines()]


def main():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("filename")
    parser.add_argument('-m', '--meta-data',  dest='metadatafile', metavar='STR', type=str, default='',
                        required=True, help='Meta-data file')
    parser.add_argument('-t', '--tobii-data',  dest='tobiifile', metavar='STR', type=str, default='',
                        required=False, help='Tobii-data file')
    parser.add_argument('-e', '--eeg-offset', dest='eeg_offset', metavar='STR', type=str, default='',
                        required=False, help='Offset for the eeg')
    parser.add_argument('-o', '--tobii-offset', dest='tobii_offset', metavar='STR', type=str, default='',
                        required=False, help='Offset for the tobii')
    # parser.add_argument("trigger_csv")
    # parser.add_argument("order")

    args = parser.parse_args()
    if not os.path.isfile(args.metadatafile):
        print("meta data file \"{0}\" could not be found.".format(args.metadatafile))
        sys.exit(0)

    time, trigger, data, parts, sr = load_data(args.filename)
    if args.tobiifile != "":
        tobii_data = load_tobii_data(args.tobiifile)
    else:
        tobii_data = False
    eeg_offset, tobii_offset = determine_offsets(time, trigger, tobii_data)
    if args.eeg_offset != "":
        eeg_offset = args.eeg_offset
    if args.tobii_offset != "":
        tobii_offset = args.tobii_offset

    # apply eeg offset to timestamp
    time = time - eeg_offset

    convert(time, trigger, data, parts, sr, tobii_data, args.metadatafile, eeg_offset, tobii_offset)


if __name__ == "__main__":
    main()
