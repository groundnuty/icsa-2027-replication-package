% Whole-domain run (#34 item 9), one shard: the authors' Step_2 as written in Step_2_MHW_detector.m,
%   [MHW,mclim,m90,mhw_ts] = detectc(SST_reshaped, time, cli_start, cli_end, mhw_start, mhw_end);
% on whole columns ja..jb (1-based, inclusive; set by --eval) of the array Step_1 builds: the N sea cells of the
% BALarea mask in the authors' order, reshaped to n x m with n = the largest prime factor of N (170171 = 379 x 449).
% detectc treats every cell on its own, so columns cut from the full array give the same values they have inside it.
% Mounts: /work (patched detectc.m and shims, ro), /tools (this file, ro), /pack (packed.f32 from pack_domain.py, ro), /out.
addpath('/work');
N = 170171; T = 15340;                      % sea cells; days 1982-01-01..2023-12-31
n = max(factor(N)); m = N / n;              % as Step_1: 449 x 379
nc = jb - ja + 1; c0 = (ja - 1) * n;
printf('Octave %s; shard columns %d..%d of %d (%d cells, first cell %d); %s\n', version(), ja, jb, m, n*nc, c0, datestr(now(), 'yyyy-mm-dd HH:MM:SS'));
f = fopen('/pack/packed.f32', 'r');
SST_reshaped = zeros(n, nc, T, 'single');
for t = 1:T
    fseek(f, ((t-1) * N + c0) * 4, 'bof');
    SST_reshaped(:, :, t) = reshape(fread(f, n*nc, 'single=>single'), n, nc);
end
fclose(f);
% ---- Step_2_MHW_detector.m, lines as written
time=datenum(1982,1,1):datenum(2023,12,31);
cli_start=datenum(1992,1,1);
cli_end=datenum(2002,12,31);
mhw_start=datenum(1982,1,2);
mhw_end=datenum(2023,12,30);
tic;
[MHW,mclim,m90,mhw_ts]=detectc(SST_reshaped,time,cli_start,cli_end,mhw_start,mhw_end);
printf('detectc took %g s; class m90 %s, mclim %s, mhw_ts %s; size mhw_ts %s\n', toc, class(m90), class(mclim), class(mhw_ts), mat2str(size(mhw_ts)));
nev = 0; for k = 1:numel(MHW), nev = nev + size(MHW{k}, 1); end
printf('cell events (rows of MHW): %d; cells with an event: %d\n', nev, sum(~cellfun(@isempty, MHW(:))));
% what Step_2 would save (MHW.mat, mclim.mat, m90.mat, mhw_ts.mat), as raw double in column-major order
g = fopen('/out/m90.f64', 'w'); fwrite(g, double(m90), 'double'); fclose(g);
g = fopen('/out/mclim.f64', 'w'); fwrite(g, double(mclim), 'double'); fclose(g);
g = fopen('/out/mhw_ts.f64', 'w'); fwrite(g, double(mhw_ts), 'double'); fclose(g);
st = fileread('/proc/self/status'); k = regexp(st, 'Vm(Peak|HWM)[^\n]*', 'match'); printf('%s\n', k{:});
printf('done %s\n', datestr(now(), 'yyyy-mm-dd HH:MM:SS'));
