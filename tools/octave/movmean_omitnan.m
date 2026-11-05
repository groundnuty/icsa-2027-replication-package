function y = movmean_omitnan(x, w)
  % centred moving mean along dim 1, NaN ignored, window shrinks at the ends (MATLAB smoothdata/movmean
  % omitnan). Each window is summed directly (offsets -h..h in turn), no prefix sums, so no cancellation.
  % (For detectc's inputs, single values near 280 K, every such sum is exact in double whatever the order.)
  sz = size(x); x = reshape(x, sz(1), []);
  h = floor(w/2); n = size(x,1);
  f = ~isnan(x); v = x; v(~f) = 0;
  s = zeros(size(x)); c = zeros(size(x));
  for k = -h:h
    src = (1:n) + k; ok = src >= 1 & src <= n;
    s(ok,:) = s(ok,:) + v(src(ok),:);
    c(ok,:) = c(ok,:) + f(src(ok),:);
  end
  y = s ./ c; y(c==0) = NaN; y = reshape(y, sz);
end
