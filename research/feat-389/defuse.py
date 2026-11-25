"""Def-use between the stage sections of build_pack.py: for each section, which earlier section's names it reads."""
import ast, re, sys, builtins
src = open(sys.argv[1], encoding="utf-8").read()
lines = src.splitlines()
marks = [(i, re.sub(r"^# -+ ", "", l)) for i, l in enumerate(lines) if re.match(r"^# -{20,} \S", l)]
bounds = [(0, "0. setup")] + marks
tree = ast.parse(src)
def sec_of(lineno):
    s = 0
    for k, (i, _) in enumerate(bounds):
        if lineno - 1 >= i: s = k
    return s
defs = {}   # name -> list of sections that assign it
uses = {}   # section -> set of names loaded
class V(ast.NodeVisitor):
    def __init__(self): self.func = 0
    def visit_FunctionDef(self, n):
        s = sec_of(n.lineno); defs.setdefault(n.name, set()).add(s)
        # names a function reads from the module scope count as reads by its section
        for m in ast.walk(n):
            if isinstance(m, ast.Name) and isinstance(m.ctx, ast.Load): uses.setdefault(s, set()).add(m.id)
    visit_ClassDef = visit_FunctionDef
    def visit_Import(self, n):
        for a in n.names: defs.setdefault((a.asname or a.name).split(".")[0], set()).add(sec_of(n.lineno))
    visit_ImportFrom = visit_Import
    def visit_Name(self, n):
        s = sec_of(n.lineno)
        if isinstance(n.ctx, (ast.Store, ast.Del)): defs.setdefault(n.id, set()).add(s)
        else: uses.setdefault(s, set()).add(n.id)
V().visit(tree)
B = set(dir(builtins))
for s, (i, title) in enumerate(bounds):
    dep = {}
    for n in sorted(uses.get(s, ())):
        if n in B: continue
        prev = [d for d in defs.get(n, ()) if d < s]
        if not prev: continue
        src_s = max(prev)
        if src_s == 0: continue
        dep.setdefault(src_s, []).append(n)
    wrote = sorted(n for n, ss in defs.items() if s in ss)
    print(f"== {title}")
    for d in sorted(dep): print(f"   <- {bounds[d][1][:28]:28s}: {', '.join(dep[d])}")
# names defined and never read later
print("\n== assigned in a stage, never read after it (top-level)")
for s, (i, title) in enumerate(bounds):
    dead = [n for n, ss in defs.items() if s in ss and max(ss) == s and not any(n in uses.get(t, ()) for t in range(s + 1, len(bounds))) and n not in uses.get(s, ())]
    if dead: print(f"   {title[:30]:30s}: {', '.join(sorted(dead))}")
