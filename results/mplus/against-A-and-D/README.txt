M+ break-even against options T and D, with M as the like-for-like reference (written 2026-11-06 06:16Z)

FILES
  breakeven-T-D.csv   one row per layout (S1, S2) x scope (required, layout) x comparator (T, D, M): 12 rows
  breakeven-T-D.json  the same rows plus the full bootstrap record per row (means, share of draws with no break-even,
                      excluded counts), the layout-P sensitivity, and the reproduction check
  compute.py          the script that made both (run with the frozen tree's venv and PYTHONPATH=<tree>)
  "no break-even" in the table means C <= W at the point estimate (or, in a CI bound, at that quantile of the draws).

CAVEATS
1. Added after seeing the data; descriptive; not in the registered M+ table (which compares M only).
2. 3 of M+'s 5 instances (I01, I06 have no T or D record).
3. Step A ran traced, with slot tokens; M+ and cold-site-f ran untraced with the admin token.
4. Step A ran at site-g (cold-site-g); nothing T or D ran at site-f, so there is no T/D cold-site-f comparator.
5. The step-A copy on this host was matched to the report's input by M's cold-site-g sample means only, not by hash.
   Additional check, run by compute.py (not part of the caveat above): the six step-A M wall_s values on I35/I37/I48 equal the six
   cold-site-g wall_s values in the registered breakeven.json inputs, value by value: yes.
Further facts:
6. Layout-scope P: the 3 layout provision events per layout carry no instance (instance is None) and each served 1-2 instances'
   runs, so P cannot be restricted by instance. The table uses all 3 per layout (n_P = 3), as the registered table does. Required-scope
   P is restricted to I35/I37/I48 by the event's instance. Sensitivity (breakeven-T-D.json, key sensitivity_*): layout-scope P kept
   only from events that served at least one layout-scope run on these 3 instances. The events' served instances are in meta.
   Cells where the sensitivity differs from the table in break_even, ci_lo or ci_hi: S2/layout/T; its n_P per layout is in the JSON.
7. Step A runs used here started between 2026-11-03T08:14:55Z and 2026-11-03T09:38:03Z (3 Nov); the M+ runs used here started between 2026-11-06T01:44:54Z and 2026-11-06T04:25:41Z (6 Nov). They were not interleaved.
8. Comparator T is option "T" only; the step-A "T-unpaginated" records (same instances, n=3 per layout) are not used.
9. Each quantity has n=3 values per cell; the bootstrap interval resamples only those 3.

METHOD (frozen tree ~/work/wt/fill-09ecc2c0, git head 09ecc2c0e657116d169dfd1e84401d44520c8aa5, clean apart from untracked .claude/)
  Functions reused unchanged: break_even_inputs icsa/scripted/mplus.py:236-270 (builds P, W and the cold-site-g C per layout; uses whole_cells icsa/scripted/mplus.py:231-233
  and drops runs with ok false); bootstrap_interval icsa/scripted/breakeven.py:39-57 (calls break_even icsa/scripted/breakeven.py:16-27); json_safe icsa/scripted/breakeven.py:60-68;
  load_runs icsa/scripted/summarize.py:13-24. The loop over layout, scope and variant is report() icsa/scripted/mplus.py:491-510, reproduced for the cold-site-g variant only, because report()
  writes into its results directory.
  Seed 20271201: the default of report()'s seed argument, equal to the seed in the registered breakeven.json. n_boot 10000 and level 0.95: the
  defaults of bootstrap_interval (report() passes only the seed).
  Inputs are filtered before the calls: M+ runs and required-scope provision events to instances I35;I37;I48; the layout-scope events are kept (caveat 6).
  C: the step-A records of the comparator's option on those instances, passed as site-g_runs with option relabelled "M" in copies (break_even_inputs
  reads only option M there; it is the cold-site-g column). For comparator M no relabel happens: like-for-like reference.
  Checks the script ran (it stops on failure): n_P = n_C = n_W = 3 in every row; P, C and W re-derived by another route (log events, run_key globs)
  and equal as sorted lists; reported means equal the means of those lists; reproduction: with all 5 M+ instances and step-A M, the four
  */cold-site-g entries of the registered breakeven.json are reproduced exactly (every field): PASS.
  Not covered by the reproduction check: T and D extraction (the registered M+ report never read T or D). They are covered only by the n and
  re-derivation assertions above.

INPUTS (read-only; sha256  path)
  b85b70068b8970a171515b9c889e7a94498f66aa00ff19d946d5b0dff7bee272  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/mplus_log.jsonl
  e605e8eb99765ea60fff5c1aa4080583c3c5e2fc6154b0e5da0c2639c0a83c8b  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/breakeven.json
  72526918427b0dd2b8ead051812903f069b1796d886fc9d38849cfad32fa1796  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-cold-site-f-p0-I48-M-S1-a1/run.json
  7742c69dbdef11f7f34e601ddc090553e24af1788f6af61f016763a182f2597e  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-cold-site-f-p0-I48-M-S2-a1/run.json
  dc7f22546df5d4e122f753540741f4d8d9066ef4ccafb6078c173e62dbf30ce5  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-cold-site-f-p1-I01-M-S2-a1/run.json
  c99213202c3f84e21eb155f844d6b5eb94aad4123ea436140f2eb80e3d48bc39  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-cold-site-f-p1-I37-M-S1-a1/run.json
  300508d07e21a53c5f1ce3f383160e9e002d46ac3c1783a314f5261aaa97f260  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-cold-site-f-p2-I01-M-S1-a1/run.json
  ddae5f23d6211a391a86a03983762aaf5ac6c3f1164c251a6fa2eba31836d4be  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-cold-site-f-p2-I06-M-S2-a1/run.json
  f2e6aaa104dfa7f25db282d59c0f585fdb95fd26c2530f12cd35f60f51a0165a  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-cold-site-f-p3-I35-M-S1-a1/run.json
  818578b5c93a7f9f4d53ebeadcca1b830a7d1b84c275aa2b2d79ad0918e61a6f  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-cold-site-f-p3-I35-M-S2-a1/run.json
  a6fa023ce84d85f795e63dd324771f7672b4a8d2e2b9035bce605c104a382861  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-cold-site-f-p4-I06-M-S1-a1/run.json
  be9d19ef6f4a804caa715571396c0d26a7ec5a7c10dcd8c8359e3631090cb8c1  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-cold-site-f-p4-I37-M-S2-a1/run.json
  36343b05941492feb49433a4e22d22b6348f32061dad58ec99f486044fd1e525  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-mplus-layout-p0-I48-Mplus-S1-a1/run.json
  78b7b40d0f77fe27d13402ca10d12ae2e89cfe1089eb31edbda8ec56b679a936  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-mplus-layout-p0-I48-Mplus-S2-a1/run.json
  6c1d2cac0066b61cb66d4db0bc7546cbd96801a182f1180c8ed61755e3a5880d  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-mplus-layout-p1-I01-Mplus-S2-a1/run.json
  1b7a5cc2262ee5335e288834f8df55699161b08d490c2bf5573c5dce535f8744  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-mplus-layout-p1-I37-Mplus-S1-a1/run.json
  e7250f7f7bd64b6b378048921fec5a4c56875a064c140dc4abb97f3f48e79a9b  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-mplus-layout-p2-I01-Mplus-S1-a1/run.json
  ab42a888ee3d7024d951ff57aa0fc4322c711bae73eeb14b1178c0f2f3fecb07  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-mplus-layout-p2-I06-Mplus-S2-a1/run.json
  76d6226266f31d99e1c4a8ed2ac553a6d39a5d295db9eb5513ab8df7aab815ac  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-mplus-layout-p3-I35-Mplus-S1-a1/run.json
  766aed9440e255ed537bce7ea15242e60551a9fbbb7a332316379c5cd283c699  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-mplus-layout-p3-I35-Mplus-S2-a1/run.json
  8167808ca6db50511666f9334ed083cc8ab990d9de0767985e132a7324b6da82  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-mplus-layout-p4-I06-Mplus-S1-a1/run.json
  fd89cf05cb0ea8572944efa6f349bbefcd3511ca1645ed6669e538c8e947acdb  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-mplus-layout-p4-I37-Mplus-S2-a1/run.json
  7a5fd95aa11d751f4a7645d2131c3bb1f1c099f0a8aea720a652153f4eeb0ef7  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-mplus-required-p0-I48-Mplus-S1-a1/run.json
  68a92dba3a104addc06de7e0cc8770e3bd79ddd9e3163575135c4b01d159486d  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-mplus-required-p0-I48-Mplus-S2-a1/run.json
  68289af4f3acdfc43b2e7a609037e933cf1c4225c7d5f8c7534e0f8b07d30c27  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-mplus-required-p1-I01-Mplus-S2-a1/run.json
  0bd7882b2a99bb77193113369d749ab1cb127e53b85be7061f3b68ba9c2f498a  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-mplus-required-p1-I37-Mplus-S1-a1/run.json
  0f3f0ebc8a4c2165a7c71a177d84ef1dbb1a1d9a635b4ba6d0704c24bdd8f8cd  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-mplus-required-p2-I01-Mplus-S1-a1/run.json
  ce1d03ad57712fb213d657e65846134398e2be0b7b12a91298655dc91b8fb965  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-mplus-required-p2-I06-Mplus-S2-a1/run.json
  1af4a67bd94daefa855e0151b17195e0ea185cee716180bca153fc4bc67469e3  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-mplus-required-p3-I35-Mplus-S1-a1/run.json
  085afbe47487175b25676122b79c88b5a12c3bcea1eb1576750b154b5f078506  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-mplus-required-p3-I35-Mplus-S2-a1/run.json
  81c8bc69a882f1e0625f3489e8d65723bf697923f18aa08468b492811bcda5e3  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-mplus-required-p4-I06-Mplus-S1-a1/run.json
  5c22a567b23eaf030fb27dbd0e256c408af9a5ef91d21dafcb01763ea5f119f9  /mnt/volume2/icsa-2027/mplus-mirror/f1c242a/runs/s12-mplus-required-p4-I37-Mplus-S2-a1/run.json
  94dd5a234e15364ed924a04e24daca6783e619280db8c2bb73829244df696887  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p0-I35-D-S1-a1/run.json
  8c3e6f149755b870cc3b78dc2b51b3f96735e7e11f1d09b562c1306df60c0340  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p0-I35-D-S2-a1/run.json
  595578de035fb6ae980e3fec39d49ad4e34fff40a3cf2b472358aa74a9d24635  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p0-I35-M-S1-a1/run.json
  5907ebac7e33769e5852d1e37a0545ac7bfd4c079214b74b08ecc57615b2f0e1  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p0-I35-M-S2-a1/run.json
  5fe5b1ceab0fe33896454aaf2bb7e4c4354bd23664806de252d4295ba42bb354  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p0-I35-T-S1-a1/run.json
  836f4175ac82287cde7db4f44e7e9cbba45ea376330e5f17f719ad789a431498  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p0-I35-T-S2-a1/run.json
  19ad8354f37991c6a1fc8279ad3cfd911ffd865cf2d1dedeeee03cb9ee8c9f44  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p0-I35-T-unpaginated-S1-a1/run.json
  e42dc3e4bcbdb638746e119cb313630e785bfe5181cfa5ec7df1526e76460422  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p0-I35-T-unpaginated-S2-a1/run.json
  28984800d0bb90ccc2f46c20bf113de22e4b2ae890e2062e1918a48148483255  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p1-I37-D-S1-a1/run.json
  67db84505794ef7fc99ba44883b3e56bdf80a7e113e864e88ca346ea709fe4d1  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p1-I37-D-S2-a1/run.json
  a25078ea6ad3b9f482d9347f156e7b0a22cae2df161c93715eed308965c95e77  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p1-I37-M-S1-a1/run.json
  d8d29f91de67360d01dda8a176a04cdb027da574907fb5204118a76a9a9c3f9f  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p1-I37-M-S2-a1/run.json
  0b3e936bc41fa0e5f721abf94c8ec9b6a38a78959661575fd8180f95372df4b2  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p1-I37-T-S1-a1/run.json
  243dd342d653b3493dceb26e7d5a0b32d45daa8f6969bcb2f8c5deb74081a436  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p1-I37-T-S2-a1/run.json
  1de57dee9f79c30d5f06ccc88117ae631f07f7691343ddf86f784f80922201c1  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p1-I37-T-unpaginated-S1-a1/run.json
  f78e0571e20e38ad384005545ea794c7c9459ff09985b21507aa4beb678da02b  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p1-I37-T-unpaginated-S2-a1/run.json
  aaf7fd638aad2921150aca8c375be1af775984128c43e89ed9526f977cbf4b85  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p2-I48-D-S1-a1/run.json
  a2f640a4b652f4b920c6e61cb2a4fb245537a341f405c2b35cfa0446ab620331  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p2-I48-D-S2-a1/run.json
  85bec73c2b0ed8b5450e3f34c01fe6f572b4366110c664f662c8337391c4bdae  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p2-I48-M-S1-a1/run.json
  94dfbfafe629d745019c807d3a2db3f0dbc62e31fc11030cea6dc392d06132b3  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p2-I48-M-S2-a1/run.json
  f3826871128591f8f34750e40fe489c151d328a24ff1aac52b64d9bbce8ce269  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p2-I48-T-S1-a1/run.json
  d059053b4fe5923436138c3fb2f873c7f1e593182300d24bd83ae9e2b9f044ea  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p2-I48-T-S2-a1/run.json
  e3f5e9fce045f398056547c57eb5f48be3b900368b943bd7b6fd8edbd65c11cc  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p2-I48-T-unpaginated-S1-a1/run.json
  610c64b48bb56a441a4fa95c227f7fd0d583a54dcbac78cbb3880a58c017d03e  /mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a/runs/s12-base-enf-p2-I48-T-unpaginated-S2-a1/run.json
  c286554f26717a48d35fc49131d4177e4dcf675f510d2d37c305db68a1ba6eca  ~/work/wt/fill-09ecc2c0/icsa/scripted/breakeven.py
  741a85d925947f164aa42c9f1a611355d632f90a6737a1bbff46c7b1c69a2e03  ~/work/wt/fill-09ecc2c0/icsa/scripted/mplus.py
  cb3fa9fb2199bb8cc88658c0e864b5460c46fa00f992ddcc38978eea9a9964ac  ~/work/wt/fill-09ecc2c0/icsa/scripted/summarize.py
  15d6648b8fa5c667f298ee38681d5b61492463cf5cfa35387b94b9bfbadecb84  /mnt/volume2/icsa-2027/mplus-breakeven-TD/compute.py
