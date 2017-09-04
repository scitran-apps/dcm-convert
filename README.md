[![Docker Pulls](https://img.shields.io/docker/pulls/scitran/dcm-convert.svg)](https://hub.docker.com/r/scitran/dcm-convert/)
[![Docker Stars](https://img.shields.io/docker/stars/scitran/dcm-convert.svg)](https://hub.docker.com/r/scitran/dcm-convert/)
# scitran/dcm-convert

SciTran DICOM Conversion Tool. Uses SciTran Data lib to convert raw DICOM data (zip) from Siemens or GE to NIfTI, Montage, and PNG (screenshots) formats. Default behavior is set in `manifest.json`.

See http://github.com/scitran/data for source code.

Example usage to generate a NIfTI and Montage archive (default behavior):
```
   docker run --rm -ti \
        -v /path/to/dicom/data:/flywheel/v0/input/dicom \
        -v /path/to/output/data:/flywheel/v0/output \
        scitran/dcm-convert \
        /flywheel/v0/input/dicom/<input_file_name> \
        /flywheel/v0/output/<output_file_base_name>
```
