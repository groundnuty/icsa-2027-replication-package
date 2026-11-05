% Run the authors' detectc.m (patched for Octave) on one block, as Step_2 calls it (defaults).
% Mounts: /work (patched code, ro), /in (meta.txt, sst.bin, ro), /out (outputs).
% meta.txt: h w T datenum_first lat0 lon0 cli_start cli_end mhw_start mhw_end (datenums as yyyymmdd)
addpath('/work');
m = fscanf(fopen('/in/meta.txt'), '%d'); h = m(1); w = m(2); T = m(3);
dn = @(x) datenum(floor(x/10000), mod(floor(x/100), 100), mod(x, 100));
t0 = dn(m(4)); cs = dn(m(7)); ce = dn(m(8)); ms = dn(m(9)); me = dn(m(10));
f = fopen('/in/sst.bin', 'r'); temp = reshape(fread(f, Inf, 'single=>single'), [h w T]); fclose(f);
time = t0 + (0:T-1);
printf('Octave %s; temp %s %dx%dx%d; baseline %s..%s; detection %s..%s\n', version(), class(temp), h, w, T, ...
       datestr(cs, 'yyyy-mm-dd'), datestr(ce, 'yyyy-mm-dd'), datestr(ms, 'yyyy-mm-dd'), datestr(me, 'yyyy-mm-dd'));
tic;
[MHW, mclim, m90, mhw_ts] = detectc(temp, time, cs, ce, ms, me);
printf('detectc took %g s; class m90 %s, mclim %s, mhw_ts %s\n', toc, class(m90), class(mclim), class(mhw_ts));
% thresholds and climatology in the precision detectc holds them; mhw_ts (anomaly, NaN = no event) as is
g = fopen('/out/m90.f64', 'w'); fwrite(g, double(m90), 'double'); fclose(g);
g = fopen('/out/mclim.f64', 'w'); fwrite(g, double(mclim), 'double'); fclose(g);
g = fopen('/out/mhw_ts.f64', 'w'); fwrite(g, double(mhw_ts), 'double'); fclose(g);
printf('wrote m90 %s, mhw_ts %s\n', mat2str(size(m90)), mat2str(size(mhw_ts)));
