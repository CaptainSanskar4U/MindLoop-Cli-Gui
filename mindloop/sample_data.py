"""Generate examples/sample-study-folder: 3-page Dijkstra PDF + complexity notes."""
from __future__ import annotations
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "examples" / "sample-study-folder"

PAGES = [
    ("Dijkstra's Algorithm - Basics",
     "Dijkstra's algorithm finds the shortest paths from a source node in a weighted graph. "
     "It works by greedily settling the closest unsettled node, again and again, until all reachable nodes are settled. "
     "Time complexity with a binary heap is O((V + E) log V). Page 1 introduces the greedy idea."),
    ("Dijkstra vs Negative Weights - Bellman-Ford",
     "Dijkstra's algorithm does NOT support negative edge weights. Once it finalizes a node it never revisits it, "
     "so a later shortcut through a negative edge is missed and the answer is wrong. "
     "Bellman-Ford DOES handle negative edge weights (but not negative cycles) by relaxing every edge repeatedly, "
     "V-1 times. Use Bellman-Ford when any weight can be negative. Page 2 is the key exam fact."),
    ("Worked Example",
     "Example: A -> B cost 4, A -> C cost 2, C -> B cost -3. Dijkstra from A settles B at 4 and stops, "
     "missing the better path A -> C -> B with total cost -1. Bellman-Ford relaxes all edges and finds -1. "
     "Rule of thumb: non-negative weights use Dijkstra; negative weights use Bellman-Ford. Page 3."),
]

MD = """# Time Complexity Notes

## Big-O
Big-O describes how runtime grows with input size n.

## Common cases
- O(1): constant, e.g. array lookup
- O(log n): binary search
- O(n): linear scan
- O(n log n): mergesort, heapsort
- O(n^2): bubble sort, insertion sort

## Sorting
Quicksort averages O(n log n) but worst case O(n^2) without good pivots.
"""

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError:
        raise SystemExit("Run: python -m pip install reportlab  then re-run this script.")
    pdf = OUT / "dijkstra-notes.pdf"
    c = canvas.Canvas(str(pdf), pagesize=letter)
    w, h = letter
    for title, body in PAGES:
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, h - 60, title)
        c.setFont("Helvetica", 12)
        y = h - 100
        words, line = body.split(), ""
        for wd in words:
            if len(line) + len(wd) + 1 > 90:
                c.drawString(50, y, line)
                y -= 20
                line = wd
            else:
                line = (line + " " + wd).strip()
        if line:
            c.drawString(50, y, line)
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(50, 40, "MINDLOOP sample material - Dijkstra vs Bellman-Ford")
        c.showPage()
    c.save()
    (OUT / "complexity.md").write_text(MD, encoding="utf-8")
    print(f"Wrote {pdf} and complexity.md in {OUT}")

if __name__ == "__main__":
    main()
