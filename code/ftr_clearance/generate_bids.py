from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path
from typing import List, Tuple


BidRow = Tuple[str, int, int, int, int]


def load_bus_numbers(data_dir: Path) -> List[int]:
    with (data_dir / "buses.csv").open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))

    if len(rows) < 3:
        raise ValueError("buses.csv does not contain enough rows.")

    header = rows[1]
    number_idx = header.index("Number")
    return [int(row[number_idx]) for row in rows[2:] if row and row[number_idx].strip()]


def choose_hot_pairs(buses: List[int]) -> List[Tuple[int, int]]:
    anchors = [bus for bus in (1, 3, 6, 8, 10, 14, 16, 21, 23, 24) if bus in buses]
    if len(anchors) < 4:
        return [(buses[0], buses[-1]), (buses[1], buses[-2])]

    return [
        (1, 14),
        (3, 24),
        (6, 13),
        (8, 21),
        (10, 18),
        (16, 4),
        (23, 6),
        (21, 8),
    ]


def generate_congested_bids(
    buses: List[int],
    count: int,
    rng: random.Random,
    hotspot_share: float,
) -> List[BidRow]:
    if len(buses) < 2:
        raise ValueError("At least two buses are required to generate bids.")

    hot_pairs = choose_hot_pairs(buses)
    bids: List[BidRow] = []

    for idx in range(1, count + 1):
        if rng.random() < hotspot_share:
            source, sink = hot_pairs[rng.randrange(len(hot_pairs))]
            if rng.random() < 0.25:
                source, sink = sink, source
            quantity = rng.randrange(80, 241, 10)
            price = rng.randrange(12, 36)
        else:
            source, sink = rng.sample(buses, 2)
            quantity = rng.randrange(30, 161, 10)
            price = rng.randrange(8, 31)

        bids.append((f"B{idx}", source, sink, quantity, price))

    return bids


def write_bids(output_path: Path, bids: List[BidRow]) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["bid_id", "source", "sink", "quantity", "price"])
        writer.writerows(bids)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate bid data for the FTR model.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory that contains buses.csv.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "bids.csv",
        help="Where to write the bid data.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=60,
        help="Number of bids to generate.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=370,
        help="Random seed for reproducible bids.",
    )
    parser.add_argument(
        "--hotspot-share",
        type=float,
        default=0.75,
        help="Fraction of bids concentrated on a few stressed source-sink pairs.",
    )
    args = parser.parse_args()

    if args.count <= 0:
        raise ValueError("--count must be positive.")
    if not 0.0 <= args.hotspot_share <= 1.0:
        raise ValueError("--hotspot-share must be between 0 and 1.")

    buses = load_bus_numbers(args.data_dir)
    rng = random.Random(args.seed)
    bids = generate_congested_bids(buses, args.count, rng, args.hotspot_share)
    write_bids(args.output, bids)
    print(
        f"Generated {len(bids)} bids at: {args.output} "
        f"(seed={args.seed}, hotspot_share={args.hotspot_share})"
    )


if __name__ == "__main__":
    main()
