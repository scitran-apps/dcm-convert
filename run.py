#!/usr/bin/env python

import os
import json
import logging
import datetime
logging.basicConfig()
log = logging.getLogger('dcmConvert')
import scitran.data as scidata


def _get_dicom_info_from_dicom(zip_file_path):
    """
    Extract the last file in the zip to /tmp/ and read it
    """
    import zipfile
    import dicom
    import os

    dicom_info = {}
    dcm = []
    if zipfile.is_zipfile(zip_file_path):
        zip = zipfile.ZipFile(zip_file_path)
        num_files = len(zip.namelist())
        for n in range((num_files -1), -1, -1):
            dcm_path = zip.extract(zip.namelist()[n], '/tmp')
            if os.path.isfile(dcm_path):
                try:
                    log.info('reading %s' % dcm_path)
                    dcm = dicom.read_file(dcm_path)
                    # Here we check for the Raw Data Storage SOP Class, if there
                    # are other DICOM files in the zip then we read the next one,
                    # if this is the only class of DICOM in the file, we accept
                    # our fate and move on.
                    if dcm.get('SOPClassUID') == 'Raw Data Storage' and n != range((num_files -1), -1, -1)[-1]:
                        continue
                    else:
                        break
                except:
                    pass
            else:
                log.warning('%s does not exist!' % dcm_path)
    else:
        log.info('Not a zip. Attempting to read %s directly' % os.path.basename(zip_file_path))
        dcm = dicom.read_file(zip_file_path)

    if dcm:
        dicom_info['StudyID'] = dcm.get('StudyID', '')
        dicom_info['SeriesNumber'] = dcm.get('SeriesNumber', '')
        dicom_info['SeriesDescription'] = dcm.get('SeriesDescription', '')
    else:
        log.warning('DICOM could not be parsed!')
        return dicom_info

    return dicom_info


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
    import os


    log.setLevel(getattr(logging, 'DEBUG'))
    logging.getLogger('[CNI-DCM-CONVERT]  ').setLevel(logging.INFO)


    OUTDIR = '/flywheel/v0/output'
    CONFIG_FILE_PATH = '/flywheel/v0/config.json'


    ############################################################################
    # Grab Config

    with open(CONFIG_FILE_PATH) as config_file:
        config = json.load(config_file)

    # Grab file info and top-level info from config
    dicom_file_path = config['inputs']['dicom']['location']['path']
    dicom_file_name = config['inputs']['dicom']['location']['name']
    output_name = config['config']['output_name'] if config['config'].has_key('output_name') else ''
    classification = config['inputs']['dicom']['object']['classification']
    ignore_series_descrip = config['config']['ignore_series_descrip']

    # Grab dicom-info from previous classifier RUN
    dicom_info = config['inputs']['dicom']['object']['info'] if config['inputs']['dicom']['object'].has_key('info') else ''

    # If it's not there, then get it from the archive
    if not dicom_info:
        dicom_info = _get_dicom_info_from_dicom(dicom_file_path)

    exam_num = dicom_info['StudyID'] if dicom_info.has_key('StudyID') else ''
    series_num = dicom_info['SeriesNumber'] if dicom_info.has_key('SeriesNumber') else ''
    series_descrip = dicom_info['SeriesDescription'] if dicom_info.has_key('SeriesDescription') else ''


    ############################################################################
    # Check series description for 'mux' string

    if not ignore_series_descrip:
        if series_descrip:
            if series_descrip.find('mux') != -1:
                log.warning('MUX string found in sereis description. Conversion will not continue! Exit(18)')
                os.sys.exit(18)
        else:
            log.warning('Series description could not be checked. Proceeding anyway!')


    ############################################################################
    # Set output name

    # Prefer the config input, then exam_num_series_num, then input DICOM file name
    if output_name:
        output_basename = output_name.split('.nii')[0] + '.nii.gz'
    elif exam_num and series_num:
        output_basename = exam_num + '_' + series_num + '_1.nii.gz'
    else:
        # Use the input file name, stripping off the zip, dcm, or dicom ext.
        log.debug('Using input filename to generate output_basename.')
        output_basename = dicom_file_name.split('.zip')[0].split('.dcm')[0].split('.dicom')[0] + '.nii.gz'
        log.debug(output_basename)
    output_name = os.path.join(OUTDIR, output_basename)


    ############################################################################
    # RUN the conversion

    log.info('Job start: %s' % datetime.datetime.utcnow())

    results = dicom_convert(dicom_file_path, output_basename)

    log.info('Job stop: %s' % datetime.datetime.utcnow())

    # Check for resutls
    if results:
        log.info('generated %s' % ', '.join(results))
        os.sys.exit(0)
    else:
        log.info('Failed.')
        os.sys.exit(1)
