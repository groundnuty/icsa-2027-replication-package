function m = nanmean(x, varargin)
  % shim for MATLAB's nanmean (Statistics Toolbox), used by the authors' Step_3: the mean ignoring NaN
  m = mean(x, varargin{:}, 'omitnan');
end
