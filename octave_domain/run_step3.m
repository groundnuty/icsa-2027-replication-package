% Whole-domain run (#34 item 9), Step_3: the authors' Step_3_MHW_event_finder.m on the MERGED mhw_ts of all shards.
% The shards' mhw_ts files are read in column order into one n x m x length(mhw_start:mhw_end) array (what Step_2 returns for the
% full domain), then the finder is the authors' text, with nanmean from the shim (mean(x,'omitnan'), as in tools/octave/run_export.m).
% Mounts: /work (shims, ro), /shards (one directory per shard: mhw_ts.f64, ro), /out. `list` (set by --eval) names the file in /shards that lists "name ja jb" per shard.
addpath('/work');
if ~exist('list', 'var'), list = 'shards.txt'; end
if ~exist('partial', 'var'), partial = false; end   % true only for a rehearsal
N = 170171; n = max(factor(N)); m = N / n; Td = datenum(2023,12,30) - datenum(1982,1,2) + 1;
printf('Octave %s; merging into %d x %d x %d; %s\n', version(), n, m, Td, datestr(now(), 'yyyy-mm-dd HH:MM:SS'));
S = textscan(fopen(['/shards/' list]), '%s %d %d'); fclose('all');
if ~partial
    cols = []; for s = 1:numel(S{1}), cols = [cols, double(S{2}(s)):double(S{3}(s))]; end
    assert(isequal(sort(cols), 1:m), 'the shard list must cover columns 1..%d exactly once', m);
end
mhw_ts = NaN(n, m, Td);
for s = 1:numel(S{1})
    ja = S{2}(s); jb = S{3}(s); nc = jb - ja + 1;
    g = fopen(['/shards/' S{1}{s} '/mhw_ts.f64'], 'r');
    mhw_ts(:, ja:jb, :) = reshape(fread(g, n*nc*Td, 'double=>double'), n, nc, Td);
    assert(isempty(fread(g, 1, 'uint8')));
    fclose(g);
end
printf('merged %d shards, %s\n', numel(S{1}), datestr(now(), 'yyyy-mm-dd HH:MM:SS'));
% ---- Step_3_MHW_event_finder.m, verbatim from here
events_mean_series=squeeze(nanmean(nanmean(mhw_ts)));

distances=find(isnan(events_mean_series));
events_tx=find(~isnan(events_mean_series));

MHW_start_end=[];
s=1;

for i=2:length(events_tx)

    if events_tx(i) - events_tx(i-1) > 1
        MHW_start_end = [MHW_start_end; events_tx(s), events_tx(i-1)];
        s = i;
    end
end

MHW_start_end = [MHW_start_end; events_tx(s), events_tx(length(events_tx))];
% ---- end of the authors' text
g = fopen('/out/events.txt', 'w'); fprintf(g, '%d %d\n', MHW_start_end'); fclose(g);
g = fopen('/out/events_mean_series.f64', 'w'); fwrite(g, double(events_mean_series(:)), 'double'); fclose(g);
printf('events %d, event days %d, active days %d of %d\n', size(MHW_start_end, 1), sum(MHW_start_end(:, 2) - MHW_start_end(:, 1) + 1), numel(events_tx), Td);
st = fileread('/proc/self/status'); k = regexp(st, 'Vm(Peak|HWM)[^\n]*', 'match'); printf('%s\n', k{:});
