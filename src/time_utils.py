from __future__ import annotations
from typing import Set, Tuple

TimeBlock = Tuple[int, int]  # (day, block)

def parse_times(times_str: str) -> Set[TimeBlock]:
  """
  Parse a times string like '1-1;1-2;3-3' into a set of (day, block).

  Rules:
  - Day is 1..7 (usually 1..5)
  - Block is 1..6 (1=early, 6=night class)
  - Items separated by ';'
  - Each item is 'day-block'

  Returns:
    set of (day, block)
  """
  times_str = (times_str or "").strip()
  if not times_str:
    return set()
  
  blocks: Set[TimeBlock] = set()
  parts = [p.strip() for p in times_str.split(";") if p.strip()]
  for part in parts:
    if "-" not in part:
      raise ValueError(f"Invalid time item: {part!r}. Expected format like'1-1'.")
    day_s, block_s = part.split("-", 1)
    day = int(day_s)
    block = int(block_s)
    if not (1 <= day <= 7):
      raise ValueError(f"Invalid day {day} in {part!r}. Day must be 1..7.")
    if not (1 <= block <= 6):
      raise ValueError(f"Invalid block {block} in {part!r}. Block must be 1..6.")
    blocks.add((day, block))
  
  return blocks