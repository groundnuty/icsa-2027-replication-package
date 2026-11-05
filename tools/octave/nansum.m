function s=nansum(x,varargin)
  x(isnan(x))=0; s=sum(x,varargin{:});
end
