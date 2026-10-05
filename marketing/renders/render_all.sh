#!/bin/sh
# Final renders of every room, one Blender process per room so each starts
# clean. Rooms already rendered are skipped; delete build/out/<room>.png to
# redo one. About 15 minutes a room on a 4-core CPU.
cd "$(dirname "$0")" || exit 1
mkdir -p build/out
for r in $(python3 -c "import rooms; print(' '.join(rooms.ROOMS))" 2>/dev/null | tail -n 1); do
  if [ -f "build/out/$r.png" ]; then echo "skip $r"; continue; fi
  echo "start $r $(date +%T)"
  python3 render_room.py "$r" --samples 256 > "build/out/$r.log" 2>&1 && echo "done $r $(date +%T)" || echo "FAILED $r"
done
echo ALL DONE
