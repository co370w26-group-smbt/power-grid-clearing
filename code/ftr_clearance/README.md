# FTR Clearance LP
## Files

- `ftr_clearance.py`: main script that reads the data, builds the LP, and solves it
- `generate_bids.py`: script for generating sample bid data
- `bids.csv`: FTR bid data
- `solution.csv`: output file with awarded MW
- `buses.csv`, `branches.csv`, `ptdf.csv`, `sf-contingencies.csv`: network data

## What The Script Does

The script decides how much of each FTR bid should be awarded.

Objective:

- maximize total bid value `sum(price * awarded_MW)`

Constraints:

- each bid cannot exceed its requested quantity
- base-case line flows must stay within branch limits
- contingency line flows must also stay within branch limits

## Bid Data Format

`bids.csv` must contain these columns:

- `bid_id`
- `source`
- `sink`
- `quantity`
- `price`

Example:

```csv
bid_id,source,sink,quantity,price
B1,1,14,100,25
B2,3,24,120,30
```

## How To Run

1. Make sure `gurobipy` is installed and your Gurobi license works on your machine.
2. Open PowerShell in the project root folder.
3. If you want sample bid data, run:

```powershell
python project\generate_bids.py
```

You can also control how bid data is generated:

```powershell
python project\generate_bids.py --count 80 --seed 370 --hotspot-share 0.85 --output project\bids.csv
```

Arguments for `generate_bids.py`:

- `--count`: number of bids to generate
- `--seed`: random seed for reproducible results
- `--hotspot-share`: fraction of bids concentrated on stressed source-sink pairs
- `--output`: output csv file name
- `--data-dir`: folder that contains `buses.csv`

4. Run the optimization:

```powershell
python project\ftr_clearance.py
```

## Output

After solving, the script creates `solution.csv`.

This file contains:

- `bid_id`
- `source`
- `sink`
- `quantity`
- `price`
- `awarded_mw`

If `awarded_mw` is smaller than `quantity`, that bid is only partially accepted.
If `awarded_mw` is `0`, that bid is rejected.

## Notes

- In this model, a `bid` is a point-to-point FTR request from one bus to another bus.
- A `branch` is a physical transmission line in the network.
- Bids are not the same as branches. Bids affect branch flows through PTDF and contingency shift factors.
- I have uploaded an example file named "bids.csv" as well as the corresponding solution for your reference.
