from __future__ import annotations

import csv
import re
from pathlib import Path

import gurobipy as gp
from gurobipy import GRB


DATA_DIR = Path(__file__).resolve().parent
BIDS_FILE = DATA_DIR / "bids.csv"
SOLUTION_FILE = DATA_DIR / "solution.csv"
USE_CONTINGENCIES = True


def read_csv_rows(path: Path):
    # The csv files in this project use the second row as the real header.
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    header = rows[1]
    data_rows = [dict(zip(header, row)) for row in rows[2:] if any(cell.strip() for cell in row)]
    return data_rows


def load_buses():
    rows = read_csv_rows(DATA_DIR / "buses.csv")
    return [int(row["Number"]) for row in rows]


def load_branches():
    rows = read_csv_rows(DATA_DIR / "branches.csv")
    branches = []
    for i, row in enumerate(rows, start=1):
        # Store each line with its thermal limit for the SFT constraints.
        branches.append(
            {
                "id": i,
                "from_bus": int(row["From Number"]),
                "to_bus": int(row["To Number"]),
                "limit": float(row["Lim MVA A"] or 0.0),
            }
        )
    return branches


def load_ptdf(branches):
    rows = read_csv_rows(DATA_DIR / "ptdf.csv")

    with (DATA_DIR / "ptdf.csv").open(newline="", encoding="utf-8-sig") as fh:
        raw_rows = list(csv.reader(fh))
    header = raw_rows[1]
    branch_columns = header[5:]

    ptdf = {}
    for row in rows:
        bus = int(row["Number"])
        ptdf[bus] = {}
        for branch, column in zip(branches, branch_columns):
            # PTDF of one bus on one monitored branch in the base case.
            ptdf[bus][branch["id"]] = float(row[column] or 0.0)
    return ptdf


def load_contingencies():
    rows = read_csv_rows(DATA_DIR / "sf-contingencies.csv")

    with (DATA_DIR / "sf-contingencies.csv").open(newline="", encoding="utf-8-sig") as fh:
        raw_rows = list(csv.reader(fh))
    header = raw_rows[1]
    scenario_columns = header[5:]

    pattern = re.compile(r".*\(MONITOR_(\d+)_.*_CONTINGENCY_(\d+)_.*\)")
    sf = {}

    for column in scenario_columns:
        match = pattern.fullmatch(column.strip())
        monitor_id = int(match.group(1))
        outage_id = int(match.group(2))
        sf[(monitor_id, outage_id)] = {}

    for row in rows:
        bus = int(row["Number"])
        for column in scenario_columns:
            match = pattern.fullmatch(column.strip())
            monitor_id = int(match.group(1))
            outage_id = int(match.group(2))
            # Shift factor of one bus under a monitor-line / outage-line pair.
            sf[(monitor_id, outage_id)][bus] = float(row[column] or 0.0)

    return sf


def load_bids():
    with BIDS_FILE.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        bids = []
        for row in reader:
            bids.append(
                {
                    "bid_id": row["bid_id"],
                    "source": int(row["source"]),
                    "sink": int(row["sink"]),
                    "quantity": float(row["quantity"]),
                    "price": float(row["price"]),
                }
            )
    return bids


def main():
    # Load all network data and bid data first.
    buses = load_buses()
    branches = load_branches()
    ptdf = load_ptdf(branches)
    bids = load_bids()

    model = gp.Model("ftr_clearance")

    x = {}
    for bid in bids:
        # x_r = awarded MW of bid r, with 0 <= x_r <= quantity.
        x[bid["bid_id"]] = model.addVar(
            lb=0.0,
            ub=bid["quantity"],
            name=f'x[{bid["bid_id"]}]',
        )

    # Maximize total bid value.
    model.setObjective(
        gp.quicksum(bid["price"] * x[bid["bid_id"]] for bid in bids),
        GRB.MAXIMIZE,
    )

    for branch in branches:
        # Base-case line flow from all awarded FTR bids together.
        flow = gp.quicksum(
            (ptdf[bid["sink"]][branch["id"]] - ptdf[bid["source"]][branch["id"]]) * x[bid["bid_id"]]
            for bid in bids
        )
        model.addConstr(flow <= branch["limit"])
        model.addConstr(flow >= -branch["limit"])

    if USE_CONTINGENCIES:
        sf = load_contingencies()
        branch_ids = {branch["id"] for branch in branches}

        for (monitor_id, outage_id), factors in sf.items():
            if monitor_id not in branch_ids or outage_id not in branch_ids:
                continue

            limit = branches[monitor_id - 1]["limit"]
            # N-1 contingency line flow constraint.
            flow = gp.quicksum(
                (factors[bid["sink"]] - factors[bid["source"]]) * x[bid["bid_id"]]
                for bid in bids
            )
            model.addConstr(flow <= limit)
            model.addConstr(flow >= -limit)

    model.optimize()

    # Save the awarded MW for each bid.
    with SOLUTION_FILE.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["bid_id", "source", "sink", "quantity", "price", "awarded_mw"])
        for bid in bids:
            writer.writerow(
                [
                    bid["bid_id"],
                    bid["source"],
                    bid["sink"],
                    bid["quantity"],
                    bid["price"],
                    x[bid["bid_id"]].X,
                ]
            )

    print("Objective value:", model.ObjVal)
    print("Solution saved to:", SOLUTION_FILE)


if __name__ == "__main__":
    main()
