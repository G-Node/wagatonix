clear all;
bla = fopen('e:\to_nix_dataset\livedata.json');
% raw = fread(bla,inf);
% str = char(raw');

pc = [];
pcmain = [];
pd = [];
pdmain = [];
gd = [];
gdmain = [];
gp = [];
gpmain = [];
gp3 = [];
gp3main = [];
gy = [];
gymain = [];
ac = [];
acmain = [];
pts = [];
ptsmain = [];
vts = [];
vtsmain = [];
evts = [];
evtsmain = [];
dir = [];
dirmain = [];

i = 0;
while ~feof(bla)
    i = i + 1;
    % reset collection structs to speed up loading times
    if (~mod(i, 5000))
        disp(i);
        pcmain = [pcmain, pc];
        pc = [];
        pdmain = [pdmain, pd];
        pd = [];
        gdmain = [gdmain, gd];
        gd = [];
        gpmain = [gpmain, gp];
        gp = [];
        gp3main = [gp3main, gp3];
        gp3 = [];
        gymain = [gymain, gy];
        gy = [];
        acmain = [acmain, ac];
        ac = [];
        ptsmain = [ptsmain, pts];
        pts = [];
        vtsmain = [vtsmain, vts];
        vts = [];
        evtsmain = [evtsmain, evts];
        evts = [];
        dirmain = [dirmain, dir];
        dir = [];
    end

    why = fgetl(bla);
    if contains(why, '"pc"')
        pc = [pc, jsondecode(why)];
    elseif contains(why, '"pd"')
        pd = [pd, jsondecode(why)];
    elseif contains(why, '"gd"')
        gd = [gd, jsondecode(why)];
    elseif contains(why, '"gp"')
        gp = [gp, jsondecode(why)];
    elseif contains(why, '"gp3"')
        gp3 = [gp3, jsondecode(why)];
    elseif contains(why, '"gy"')
        gy = [gy, jsondecode(why)];
    elseif contains(why, '"ac"')
        ac = [ac, jsondecode(why)];
    elseif contains(why, '"pts"')
        pts = [pts, jsondecode(why)];
    elseif contains(why, '"vts"')
        vts = [vts, jsondecode(why)];
    elseif contains(why, '"evts"')
        evts = [evts, jsondecode(why)];
    elseif contains(why, '"dir"')
        dir = [dir, jsondecode(why)];
    end

end

pcmain = [pcmain, pc];
pdmain = [pdmain, pd];
gdmain = [gdmain, gd];
gpmain = [gpmain, gp];
gp3main = [gp3main, gp3];
gymain = [gymain, gy];
acmain = [acmain, ac];
ptsmain = [ptsmain, pts];
vtsmain = [vtsmain, vts];
evtsmain = [evtsmain, evts];
dirmain = [dirmain, dir];

fclose(bla);

clear pc pd gd gp gp3 gy ac pts vts evts dir bla;


