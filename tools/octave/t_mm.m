addpath('/work');
disp(movmean_omitnan([1;NaN;3;4;5],3)');
x=reshape(1:8,1,1,8); y=permute(movmean_omitnan(permute(x,[3 1 2]),3),[2 3 1]); disp(squeeze(y)');
