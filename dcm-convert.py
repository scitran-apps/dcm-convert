#!/usr/bin/env python

import os
import json
import logging
import datetime
logging.basicConfig()
log = logging.getLogger('dcmConvert')
import scitran.data as scidata


def dicom_convert(fp, outbase=None):
    """
    Attempts multiple types of conversion on dicom files.

    Attempts to create a nifti for all files, except screen shots.
    Also attempts to create montages of all files.

    """
    if not os.path.exists(fp):
        print 'could not find %s' % fp
        print 'checking input directory ...'
        if os.path.exists(os.path.join('/input', fp)):
            fp = os.path.join('/input', fp)
            print 'found %s' % fp

    if not outbase:
        fn = os.path.basename(fp)
        outbase = os.path.join('/output', fn[:fn.index('_dicom')])   # take everything before dicom...
        log.info('setting outbase to %s' % outbase)


    # CONFIG: If there is a config file then load that, else load the manifest and read the default values.
    if os.path.exists('/flywheel/v0/config.json'):
        config_file = '/flywheel/v0/config.json'
        MANIFEST=False
    else:
        config_file = '/flywheel/v0/manifest.json'
        MANIFEST=True

    with open(config_file, 'r') as jsonfile:
        config = json.load(jsonfile)
    config = config.pop('config')

    if MANIFEST:
        convert_montage = config['convert_montage']['default']
        convert_nifti = config['convert_nifti']['default']
        convert_png = config['convert_png']['default']
    else:
        convert_montage = config['convert_montage']
        convert_nifti = config['convert_nifti']
        convert_png = config['convert_png']


    # CONVERSION
    log.info('converting dicom file %s' % fp)
    ds = scidata.parse(fp, filetype='dicom', ignore_json=True, load_data=True)
    log.info('loaded and parsed')

    final_results = []
    # create nifti and Montage
    if ds.scan_type != 'screenshot':
        if convert_montage:
            log.info('performing non screenshot conversion, montage')
            final_results += scidata.write(ds, ds.data, outbase=outbase + '.montage', filetype='montage', voxel_order='LPS')  # always LPS
        if convert_nifti:
            log.info('performing non screenshot conversion, nifti')
            final_results += scidata.write(ds, ds.data, outbase=outbase, filetype='nifti')  # no reorder

    elif ds.scan_type == 'screenshot':
        if convert_png:
            log.info('performing screenshot conversion, png')
            final_results += scidata.write(ds, ds.data, outbase=outbase + '.screenshot', filetype='png')

    # Write metadata file
    output_files = os.listdir(os.path.dirname(outbase))
    files = []
    if len(output_files) > 0:
        for f in output_files:

            fdict = {}
            fdict['name'] = f

            if f.endswith('.nii.gz'):
                ftype = 'nifti'

            elif f.endswith('bvec'):
                ftype = 'bvec'

            elif f.endswith('bval'):
                ftype = 'bval'

            elif f.endswith('montage.zip'):
                ftype = 'montage'

            elif f.endswith('.png'):
                ftype = 'screenshot'

            else:
                ftype = 'None'

            fdict['type'] = ftype
            files.append(fdict)

        metadata = {}
        metadata['acquisition'] = {}
        metadata['acquisition']['files'] = files

        with open(os.path.join(os.path.dirname(outbase),'.metadata.json'), 'w') as metafile:
            json.dump(metadata, metafile)

    return final_results

if __name__ == '__main__':
    """
    Run dcm-convert on input dicom file
    """
    import json

    log.setLevel(getattr(logging, 'DEBUG'))
    logging.getLogger('[CNI-DCM-CONVERT]  ').setLevel(logging.INFO)

    # Grab Config
    CONFIG_FILE_PATH = '/flywheel/v0/config.json'
    with open(CONFIG_FILE_PATH) as config_file:
        config = json.load(config_file)

    dicom_file_path = config['inputs']['dicom']['location']['path']
    dicom_file_name = config['inputs']['dicom']['location']['name']
    output_name = config['config']['output_name'] if config['config'].has_key('output_name') else ''
    classification = config['inputs']['dicom']['object']['classification']
    ignore_series_descrip = config['config']['ignore_series_descrip']

    dicom_info = config['inputs']['dicom']['object']['info']
    exam_num = dicom_info['StudyID'] if dicom_info.has_key('StudyID') else ''
    series_num = dicom_info['SeriesNumber'] if dicom_info.has_key('SeriesNumber') else ''
    series_descrip = dicom_info['SeriesDescription'] if dicom_info.has_key('SeriesDescription') else ''

    # Set output name. Prefer the config input, then exam_num_series_num, then
    # Input file name.
    OUTDIR = '/flywheel/v0/output'
    if output_name:
        output_basename = output_name.split('.nii')[0] + '.nii.gz'
    elif exam_num and series_num:
        output_basename = exam_num + '_' + series_num + '_1.nii.gz'
    else:
        # Use the input file name, stripping off the zip, dcm, or dicom ext.
        output_basename = dicom_file_name.split('.zip')[0].split('.dcm')[0].split('.dicom')[0] + '.nii.gz'
    output_name = os.path.join(OUTDIR, output_basename)

    log.info('Job start: %s' % datetime.datetime.utcnow())

    # RUN the conversion
    results = dicom_convert(dicom_file_path, output_basename)

    log.info('Job stop: %s' % datetime.datetime.utcnow())

    # Check for resutls
    if results:
        log.info('generated %s' % ', '.join(results))
        os.sys.exit(0)
    else:
        log.info('Failed.')
        os.sys.exit(1)
