% Round trip of the authors' export (science review of #4, 2b): Step_2 -> Step_3 -> Step_4 under Octave.
% Mounts: /work (patched detectc.m and shims, from prepare.sh, ro), /tools (this file, nanmean.m, ro),
%         /in (meta.txt, sst.bin from make_input.py, ro), /out (outputs).
% Step_2 is called as written: detectc(temp, time, cli_start, cli_end, mhw_start, mhw_end), defaults.
% Step_3's event finder and Step_4's time labels are copied verbatim. Only file I/O is replaced: the
% .mat saves and the netCDF writes become binary files. Step_1's packing of sea cells (not_nan_idx) is a
% permutation of cells; here every block cell is kept, so not_nan_idx is the identity.
addpath('/work'); addpath('/tools');
m = fscanf(fopen('/in/meta.txt'), '%d'); h = m(1); w = m(2); T = m(3);
dn = @(x) datenum(floor(x/10000), mod(floor(x/100), 100), mod(x, 100));
t0 = dn(m(4)); cli_start = dn(m(7)); cli_end = dn(m(8)); mhw_start = dn(m(9)); mhw_end = dn(m(10));
f = fopen('/in/sst.bin', 'r'); SST_reshaped = reshape(fread(f, Inf, 'single=>single'), [h w T]); fclose(f);
time = t0 + (0:T-1);
printf('Octave %s; SST %dx%dx%d from %s; detection %s..%s\n', version(), h, w, T, datestr(t0, 'yyyy-mm-dd'), ...
       datestr(mhw_start, 'yyyy-mm-dd'), datestr(mhw_end, 'yyyy-mm-dd'));

% ---- Step_2_MHW_detector.m
[MHW, mclim, m90, mhw_ts] = detectc(SST_reshaped, time, cli_start, cli_end, mhw_start, mhw_end);

% ---- Step_3_MHW_event_finder.m (verbatim logic)
events_mean_series = squeeze(nanmean(nanmean(mhw_ts)));
distances = find(isnan(events_mean_series));
events_tx = find(~isnan(events_mean_series));
MHW_start_end = [];
s = 1;
for i = 2:length(events_tx)
    if events_tx(i) - events_tx(i-1) > 1
        MHW_start_end = [MHW_start_end; events_tx(s), events_tx(i-1)];
        s = i;
    end
end
MHW_start_end = [MHW_start_end; events_tx(s), events_tx(length(events_tx))];

% ---- Step_4_NCfile_generator.m: mhw_time = datetime(1982,1,2,12,0,0):days(1):datetime(2023,12,30,12,0,0);
%      dt = mhw_time(MHW_start_end(num,1):MHW_start_end(num,2)); time = posixtime(dt); MHW_int_maps = single(MHW_event)
mhw_time = datenum(1982,1,2,12,0,0):1:datenum(2023,12,30,12,0,0);
gm = fopen('/out/maps.f32', 'w'); gt = fopen('/out/time.f64', 'w');
for num = 1:size(MHW_start_end, 1)
    t1 = MHW_start_end(num, 1); t2 = MHW_start_end(num, 2);
    MHW_event = mhw_ts(:, :, t1:t2);
    dtn = mhw_time(t1:t2);
    posix = (dtn - datenum(1970, 1, 1)) * 86400;
    fwrite(gm, single(MHW_event), 'single');
    fwrite(gt, posix, 'double');
end
fclose(gm); fclose(gt);
g = fopen('/out/events.txt', 'w'); fprintf(g, '%d %d\n', MHW_start_end'); fclose(g);
% ---- Step_5_SUPPNCdatagenerator.m: mclim = single(mclim)
g = fopen('/out/mclim.f32', 'w'); fwrite(g, single(mclim), 'single'); fclose(g);
printf('events %d, event days %d; class mhw_ts %s, mclim %s\n', size(MHW_start_end, 1), ...
       sum(MHW_start_end(:, 2) - MHW_start_end(:, 1) + 1), class(mhw_ts), class(mclim));
