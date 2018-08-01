#!/usr/bin/env python

import os
import json
import logging
import datetime
import scitran.data as scidata

logging.basicConfig()
log = logging.getLogger(' [ stanfordcni/cni-dcm-convert ] ')
log.setLevel(getattr(logging, 'DEBUG'))


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


def dicom_convert(fp, classification, modality, outbase):
    """
    Attempts multiple types of conversion on dicom files.

    Attempts to create a nifti for all files, except screen shots.
    Also attempts to create montages of all files.

    """
    import pprint
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
    log.info('Converting dicom file %s...' % fp)
    ds = scidata.parse(fp, filetype='dicom', ignore_json=True, load_data=True)
    log.info('Loaded and parsed.')

    final_results = []
    # create nifti and Montage
    if ds.scan_type != 'screenshot':
        if convert_montage:
            log.info('Performing montage conversion...')
            final_results += scidata.write(ds, ds.data, outbase=outbase + '.montage', filetype='montage', voxel_order='LPS')  # always LPS
        if convert_nifti:
            log.info('Performing NIfTI conversion...')
            final_results += scidata.write(ds, ds.data, outbase=outbase, filetype='nifti')  # no reorder

    elif ds.scan_type == 'screenshot':
        if convert_png:
            log.info('Performing screenshot conversion to png...')
            final_results += scidata.write(ds, ds.data, outbase=outbase + '.screenshot', filetype='png')


    # METADATA
    output_files = os.listdir(os.path.dirname(outbase))
    files = []
    if len(output_files) > 0:
        for f in output_files:

            fdict = {}
            fdict['name'] = f

            # Set filetype
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
                ftype = None
            if ftype:
                fdict['type'] = ftype

            # Set classification and modality
            if classification:
                fdict['classification'] = classification
            else:
                log.info('No classification was passed in! Not setting on outputs.')
            if modality:
                fdict['modality'] = modality
            else:
                log.info('No modality was passed in! Not setting on outputs.')

            files.append(fdict)

        metadata = {}
        metadata['acquisition'] = {}
        metadata['acquisition']['files'] = files

        with open(os.path.join(os.path.dirname(outbase),'.metadata.json'), 'w') as metafile:
            json.dump(metadata, metafile)

    log.info('Metadata output:')
    pprint.pprint(metadata)

    return final_results

if __name__ == '__main__':
    """
    Run dcm-convert on input dicom file
    """

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
    ignore_series_descrip = config['config']['ignore_series_descrip']
    config_ojb = config['inputs']['dicom']['object']

    # Grab dicom-info from previous classifier RUN
    if config_ojb.has_key('classification'):
        classification = config_ojb['classification']
    else:
        log.info('No classification was found in the config.')
        classification = []
    if config_ojb.has_key('modality'):
        modality = config_ojb['modality']
    else:
        log.info('No modality was found in the config - setting to MR')
        modality = 'MR'

    dicom_info = config_ojb['info'] if config_ojb.has_key('info') else ''

    # If dicom info is not there, then get it from the archive
    if not dicom_info or not dicom_info.has_key('StudyID') or not dicom_info.has_key('SeriesNumber') or not dicom_info.has_key('SeriesDescription'):
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
        output_basename = output_name.split('.nii')[0]
    elif exam_num and series_num:
        output_basename = str(exam_num) + '_' + str(series_num) + '_1' # HACK how do we get the sub-series number?
    else:
        # Use the input file name, stripping off the zip, dcm, or dicom ext.
        log.debug('Using input filename to generate output_basename.')
        output_basename = dicom_file_name.split('.zip')[0].split('.dcm')[0].split('.dicom')[0]

    output_basename = os.path.join(OUTDIR, output_basename)
    log.debug('Output base name set to %s' % output_basename)


    ############################################################################
    # RUN the conversion

    log.info('Job start: %s' % datetime.datetime.utcnow())

    results = dicom_convert(dicom_file_path, classification, modality, output_basename)

    log.info('Job stop: %s' % datetime.datetime.utcnow())

    # Check for resutls
    if results:
        log.info('generated %s' % ', '.join(results))
        os.sys.exit(0)
    else:
        log.info('Failed.')
        os.sys.exit(1)
