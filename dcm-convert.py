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
            final_results += scidata.write(ds, ds.data, outbase=outbase + '_montage', filetype='montage', voxel_order='LPS')  # always LPS
        if convert_nifti:
            log.info('performing non screenshot conversion, nifti')
            final_results += scidata.write(ds, ds.data, outbase=outbase + '_nifti', filetype='nifti')  # no reorder

    elif ds.scan_type == 'screenshot':
        if convert_png:
            log.info('performing screenshot conversion, png')
            final_results += scidata.write(ds, ds.data, outbase=outbase + '_png', filetype='png')

    return final_results

if __name__ == '__main__':

    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('dcmtgz', help='path to dicom zip')
    ap.add_argument('outbase', nargs='?', help='outfile name prefix')
    ap.add_argument('--log_level', help='logging level', default='info')
    args = ap.parse_args()

    log.setLevel(getattr(logging, args.log_level.upper()))
    logging.getLogger('sctran.data').setLevel(logging.INFO)

    log.info('job start: %s' % datetime.datetime.utcnow())
    results = dicom_convert(args.dcmtgz, args.outbase)
    log.info('job stop: %s' % datetime.datetime.utcnow())
    if results:
        log.info('generated %s' % ', '.join(results))
    else:
        log.info('Failed.')
