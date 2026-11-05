% Octave semantics that the equivalence run depends on (issue #4).
% Every expected value is worked out by hand from MATLAB's documented behaviour:
%   quantile (default): the sorted non-NaN values are the (k-0.5)/n quantiles, linear in between,
%     clamped to min/max outside [0.5/n, (n-0.5)/n]; NaN is ignored.
%   smoothdata(...,'movmean',w): centred window, NaN omitted by default, window shrinks at the ends.
%   relational operators on single vs double compare the exact values (single(0.1) == 0.1 is false).
% Run: docker run --rm --network none -v <dir with this file and movmean_omitnan.m>:/work:ro \
%        gnuoctave/octave:9.2.0 octave-cli --eval "addpath('/work'); t_semantics"
function t_semantics()
  printf('Octave %s\n', version());
  nfail = 0;
  nfail += chk('quantile(1:10, .9)', quantile(1:10, 0.9), 9.5);
  nfail += chk('quantile([1 2 3 4 NaN], .9): NaN ignored, clamp to max', quantile([1 2 3 4 NaN], 0.9), 4);
  nfail += chk('quantile([3 1 NaN 2], .5)', quantile([3 1 NaN 2], 0.5), 2);
  nfail += chk('quantile([10 20 30 40 50 NaN NaN], .7)', quantile([10 20 30 40 50 NaN NaN], 0.7), 40);
  nfail += chk('quantile([10 20 30 40 50 NaN NaN], .75)', quantile([10 20 30 40 50 NaN NaN], 0.75), 42.5);
  nfail += chk('quantile([10 20 30 40 50], .05): clamp to min', quantile([10 20 30 40 50], 0.05), 10);
  nfail += chk('quantile(1:121, .9)', quantile(1:121, 0.9), 109.4);
  nfail += chk('quantile([NaN 5], .9): one value', quantile([NaN 5], 0.9), 5);
  nfail += chk('quantile([NaN NaN], .9): all NaN', quantile([NaN NaN], 0.9), NaN);
  x = zeros(1, 2, 10); x(1, 1, :) = 1:10; x(1, 2, :) = [1:9 NaN];
  nfail += chk('quantile(x, .9, 3), per cell NaN counts', reshape(quantile(x, 0.9, 3), 1, []), [9.5 8.6]);
  % movmean shim (the patch's replacement for smoothdata movmean)
  nfail += chk('movmean_omitnan([1 NaN 3 4 5], 3)', movmean_omitnan([1; NaN; 3; 4; 5], 3)', [1 2 3.5 4 4.5]);
  nfail += chk('movmean_omitnan([NaN NaN 3], 3)', movmean_omitnan([NaN; NaN; 3], 3)', [NaN 3 3]);
  nfail += chk('movmean_omitnan(1:6, 5): shrinking ends', movmean_omitnan((1:6)', 5)', [2 2.5 3 4 4.5 5]);
  y = movmean_omitnan([1 10; 2 NaN; 3 30], 3);
  nfail += chk('movmean_omitnan on columns', y(:)', [1.5 2 2.5 10 20 30]);
  z = reshape(1:8, 1, 1, 8);
  nfail += chk('movmean_omitnan along dim 3 as the patch calls it', ...
               squeeze(permute(movmean_omitnan(permute(z, [3 1 2]), 3), [2 3 1]))', [1.5 2 3 4 5 6 7 7.5]);
  printf('FAILURES: %d\n', nfail);
  % Precision facts for the detectc chain (reported, not asserted)
  a = NaN(2, 2, 3); a(:, :, 1) = single(ones(2));
  printf('class after assigning single into NaN(...) (double) array: %s\n', class(a));
  s = single(280.15 * ones(1, 121));
  q = quantile(s, 0.9);
  printf('class(quantile(single)) = %s; equal-values quantile exact: %d (diff %g)\n', class(q), q == s(1), double(q) - double(s(1)));
  m = mean(reshape(single(280 + (1:121) / 100), 1, 1, 121), 3, 'omitnan');
  printf('class(mean(single, omitnan)) = %s\n', class(m));
  printf('single(0.1) == 0.1 -> %d (1: Octave compares single vs double in single precision; MATLAB unverified, no licence)\n', single(0.1) == 0.1);
  printf('class(single - double) = %s\n', class(single(1) - 0.5));
end

function f = chk(name, got, want)
  ok = isequal(size(got), size(want)) && all((abs(double(got) - want) < 1e-12) | (isnan(got) & isnan(want)));
  f = ~ok;
  if ok
    printf('PASS %s = %s\n', name, mat2str(double(got), 6));
  else
    printf('FAIL %s = %s, expected %s\n', name, mat2str(double(got), 6), mat2str(want, 6));
  end
end
