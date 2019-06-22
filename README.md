[![Docker Pulls](https://img.shields.io/docker/pulls/stanfordcni/cni-dcm-convert.svg)](https://hub.docker.com/r/stanfordcni/cni-dcm-convert/)
[![Docker Stars](https://img.shields.io/docker/stars/stanfordcni/cni-dcm-convert.svg)](https://hub.docker.com/r/stanfordcni/cni-dcm-convert/)
# stanfordcni/cni-dcm-convert

Build context for a [Flywheel Gear](https://github.com/flywheel-io/gears/tree/master/spec) which runs the SciTran DICOM Conversion Tool used at the [Stanford CNI](cni.stanford.edu). This Gear uses the SciTran Data lib to convert raw DICOM data (zip) from Siemens or GE to NIfTI, Montage, and PNG (screenshots) formats. Default behavior is set in `manifest.json`.

See http://github.com/vistalab/scitran-data for source code.
