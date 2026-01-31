import re
EP_RE = re.compile(r"^Ep(\d+)(?:-(\d+))?$")
def parse_ep(text):
    m = EP_RE.match(text or "")
    if not m: return None
    a = int(m.group(1))
    b = int(m.group(2)) if m.group(2) else a
    return a, b
