# Descending neurons for brain-body mapping (FlyWire v783)

Side labels follow the FlyWire v783 annotation table (soma side, `side` column), NOT the
left/right names in Eon's example.ipynb (several of those are swapped).

## Steering (verified)

Source: Rayshubskiy et al. 2025, eLife 13:RP102230, doi:10.7554/eLife.102230.3 (Methods, "EM reconstruction").

| Type  | Side  | root_id            | Status |
|-------|-------|--------------------|--------|
| DNa02 | left  | 720575940629327659 | [DATA] IDs from the paper, match annotation table |
| DNa02 | right | 720575940604737708 | [DATA] |
| DNa01 | left  | 720575940627787609 | [DATA] FlyWire cell_type DNa01 (hemibrain VES006) |
| DNa01 | right | 720575940644438551 | [DATA] |

- Do NOT use the pair with cell_type DNae001 (annotation hemibrain_type "DNa01"): the paper states
  that neurons labelled DNa01 in hemibrain v1.2.1 are different from the SS00731 pair.
- [DATA] Whole-cell recordings on a spherical treadmill: both types fire before ipsilateral turns;
  turning velocity is ~linear in the right-left difference of firing rate (shown for DNa02,
  similar for DNa01). DNa02 has the higher steering gain.
- [SIMPLIFICATION] Steering in the model will be read out from 2 DN types only; the paper notes
  that many other DNs contribute (e.g. DNa03), and bilateral silencing did not change rotation
  in freely walking flies.
- [HYPOTHESIS] Appetitive/aversive turning via MBON32 -> DNa02 (paper's proposal, untested here).

## Forward speed (unresolved)

- DNp09: left 720575940635872101, right 720575940627652358 (annotation table). The paper cites
  Bidaye et al. 2020 for DNp09 (P9): promotes forward speed AND ipsilateral steering, so it is not
  a pure speed neuron.
- DNg97 (left 720575940626730883, right 720575940620300308) is what Eon's notebook calls
  "P9_oDN1". The name mapping is NOT verified; no function confirmed for these IDs.
- DNg100 is in the annotation table; role not verified for the FlyWire IDs.
- Prototype: constant forward drive [SIMPLIFICATION].

## MN9 (feeding motor neurons, nerve PhN)

- 720575940660219265 (annotation side=right), 720575940618238523 (annotation side=left).
- 720575940645521262 is from release 630 and is absent from the 783 model.
