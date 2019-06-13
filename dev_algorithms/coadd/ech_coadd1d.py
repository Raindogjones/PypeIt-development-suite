import os
import numpy as np
from astropy.io import fits
import matplotlib.pyplot as plt

#from pypeit.core import coadd1d
#from coadd1d_old import *
from pypeit.core.coadd1d import *
from pypeit.core import load



datapath = os.path.join(os.getenv('HOME'), 'Dropbox/PypeIt_Redux/NIRES/NIRES_May19/Science/')
fnames = [datapath + 'spec1d_flux_s190519_0037-J1007+2115_NIRES_2019May19T055221.895.fits',
          datapath + 'spec1d_flux_s190519_0038-J1007+2115_NIRES_2019May19T055923.665.fits',
          datapath + 'spec1d_flux_s190519_0041-J1007+2115_NIRES_2019May19T062048.865.fits',
          datapath + 'spec1d_flux_s190519_0042-J1007+2115_NIRES_2019May19T062750.635.fits',
          datapath + 'spec1d_flux_s190519_0045-J1007+2115_NIRES_2019May19T064943.885.fits',
          datapath + 'spec1d_flux_s190519_0046-J1007+2115_NIRES_2019May19T065646.165.fits',
          datapath + 'spec1d_flux_s190519_0049-J1007+2115_NIRES_2019May19T071920.215.fits',
          datapath + 'spec1d_flux_s190519_0050-J1007+2115_NIRES_2019May19T072621.985.fits',
          datapath + 'spec1d_flux_s190519_0053-J1007+2115_NIRES_2019May19T074819.315.fits',
          datapath + 'spec1d_flux_s190519_0054-J1007+2115_NIRES_2019May19T075521.595.fits',
          datapath + 'spec1d_flux_s190519_0057-J1007+2115_NIRES_2019May19T081918.265.fits',
          datapath + 'spec1d_flux_s190519_0058-J1007+2115_NIRES_2019May19T082620.545.fits']

gdobj = ['OBJ0001', 'OBJ0001', 'OBJ0001', 'OBJ0001',
         'OBJ0001', 'OBJ0001', 'OBJ0001', 'OBJ0001',
         'OBJ0001', 'OBJ0001', 'OBJ0001', 'OBJ0001']
# parameters for load_1dspec_to_array
ex_value = 'OPT'
flux_value = True

outfile = 'J1007'
norder = 5


from IPython import embed
embed()


# Load data
waves, fluxes, ivars, masks = load.load_1dspec_to_array(fnames, gdobj=gdobj, order=None, ex_value=ex_value, flux_value=flux_value)
scales = np.zeros_like(waves)
weights = np.zeros_like(waves)
outmasks = np.zeros_like(waves,dtype=bool)
npix = int(np.shape(waves)[0]/norder) # detector size in the wavelength direction

# arrays to store stacked individual order spectra. I set npix_stack = npix*2 to make sure
waves_stack_orders = np.zeros((npix*2, norder))
fluxes_stack_orders = np.zeros((npix*2, norder))
ivars_stack_orders = np.zeros((npix*2, norder))
masks_stack_orders = np.zeros((npix*2, norder),dtype=bool)

# Loop over orders to get the initial stack and scale factor or each order
for ii in range(norder):

    # get the slice of iord spectra of all exposures
    waves_iord, fluxes_iord, ivars_iord, masks_iord = waves[npix*ii:npix*(ii+1),:], fluxes[npix*ii:npix*(ii+1),:], \
                                                      ivars[npix*ii:npix*(ii+1),:], masks[npix*ii:npix*(ii+1),:]

    # Get the stacked spectrum for each order
    # Todo: save stacked individual order spectra into one single fits
    if outfile is not None:
        outfile_order = 'spec1d_stack_order{:04d}_{:}'.format(ii,outfile)
    wave_stack_iord, flux_stack_iord, ivar_stack_iord, mask_stack_iord, outmask_iord, weights_iord, scales_iord, rms_sn_iord = \
                long_combspec(waves_iord, fluxes_iord, ivars_iord, masks_iord, wave_grid_method='loggrid',
                              wave_grid_min=None, wave_grid_max=None, A_pix=None, v_pix=None, samp_fact = 1.0,
                              ref_percentile=20.0, maxiter_scale=5, sigrej=3, scale_method=None, hand_scale=None,
                              sn_max_medscale=2.0, sn_min_medscale=0.5, dv_smooth=10000.0, const_weights=False,
                              maxiter_reject=5, sn_cap=20.0, lower=3.0, upper=3.0, maxrej=None, qafile=None,
                              outfile=outfile_order, debug=True)

    # store individual stacked spectrum
    npix_stack = np.size(wave_stack_iord)
    waves_stack_orders[:npix_stack, ii] = wave_stack_iord
    fluxes_stack_orders[:npix_stack, ii] = flux_stack_iord
    ivars_stack_orders[:npix_stack, ii] = ivar_stack_iord
    masks_stack_orders[:npix_stack, ii] = mask_stack_iord

    # store new masks, scales and weights, all of these arrays are in native wave grid
    scales[ii*npix:(ii+1)*npix, :] = scales_iord.copy()
    weights[ii*npix:(ii+1)*npix, :] = weights_iord.copy()
    outmasks[ii*npix:(ii+1)*npix, :] = outmask_iord.copy()


debug = True
max_factor = 10.0
wave_method = 'loggrid'


order_ratios = np.ones(norder)
## re-scale bluer orders to match the reddest order.
# scaling spectrum order by order. We use the reddest order as the reference since slit loss in redder is smaller
for ii in range(norder - 1):
    iord = norder - ii - 1

    wave_blue, flux_blue, ivar_blue, mask_blue = waves_stack_orders[:, iord-1], fluxes_stack_orders[:, iord-1],\
                                                 ivars_stack_orders[:, iord-1], masks_stack_orders[:, iord-1]

    wave_red, flux_red, ivar_red, mask_red = waves_stack_orders[:, iord], fluxes_stack_orders[:, iord]*order_ratios[iord],\
                                             ivars_stack_orders[:, iord]*1.0/order_ratios[iord]**2, masks_stack_orders[:, iord]

    # interpolate iord-1 (bluer) to iord-1 (redder)
    flux_tmp, ivar_tmp, mask_tmp = interp_spec(wave_red, wave_blue, flux_blue, ivar_blue, mask_blue)

    npix_overlap = np.sum(mask_tmp & mask_red)
    percentile_iord = np.fmax(100.0 * (npix_overlap / np.sum(mask_red)-0.05), 10)

    order_ratio_iord = robust_median_ratio(flux_tmp, ivar_tmp, flux_red, ivar_red, mask=mask_tmp,
                                               mask_ref=mask_red, ref_percentile=percentile_iord, min_good=0.05,
                                               maxiters=5, max_factor=10.0, sigrej=3.0)

    order_ratios[iord - 1] = np.fmax(np.fmin(order_ratio_iord, max_factor), 1.0/max_factor)
    msgs.info('Scaled {}th order to {}th order by {:}'.format(order_vec[iord-1],order_vec[iord],order_ratios[iord-1]))

    if debug:
        plt.figure(figsize=(12, 8))
        plt.plot(wave_red[mask_red], flux_red[mask_red], 'k-', label='reference spectrum')
        plt.plot(wave_blue[mask_blue], flux_blue[mask_blue],color='dodgerblue', lw=3, label='raw spectrum')
        plt.plot(wave_blue[mask_blue], flux_blue[mask_blue]*order_ratios[iord-1], color='r',
                 alpha=0.5, label='re-scaled spectrum')

        med_width = (2.0 * np.ceil(0.03 / 2.0 * wave_blue[mask_blue].size) + 1).astype(int)
        flux_med, ivar_med = median_filt_spec(flux_blue, ivar_blue, mask_blue, med_width)
        ymax = 1.5 * flux_med.max()
        ymin = -0.15 * ymax

        plt.ylim([ymin, ymax])
        plt.xlim([np.min(wave_blue[mask_blue]), np.max(wave_red[mask_red])])
        plt.legend()
        plt.xlabel('wavelength')
        plt.ylabel('Flux')
        plt.show()

# apply order_ratios to the scales array: order_ratio*scale
scales_new = np.copy(scales)
for ii in range(norder):
    scales_new[ii*npix:(ii+1)*npix,:] *= order_ratios[ii]

fluxes_scale = fluxes * scales_new
ivars_scale = ivars * 1.0/scales_new**2

wave_grid = new_wave_grid(waves, wave_method=wave_method, wave_grid_min=None, wave_grid_max=None,
                          A_pix=None, v_pix=None, samp_fact=1.0)

#wave_ref, flux_ref, ivar_ref, mask_ref, nused = compute_stack(waves, fluxes_scale, ivars_scale, masks, wave_grid, weights)
wave_stack, flux_stack, ivar_stack, mask_stack, outmask, weights, scales = spec_reject(
    waves, fluxes_scale, ivars_scale, masks, weights, wave_grid, debug=True)
write_to_fits(wave_stack, flux_stack, ivar_stack, mask_stack, 'J1007_NIRES_Coadd.fits', clobber=True)


from IPython import embed
embed()

for ii in range(norder):
    plt.plot(waves_stack_orders[:, ii][masks_stack_orders[:, ii]], fluxes_stack_orders[:, ii][masks_stack_orders[:, ii]])
plt.ylim([ymin, ymax])
plt.show()

for ii in range(norder):
    plt.plot(waves_stack_orders[:, ii][masks_stack_orders[:, ii]], order_ratios[ii]*fluxes_stack_orders[:, ii][masks_stack_orders[:, ii]])
plt.ylim([ymin, ymax])
plt.show()