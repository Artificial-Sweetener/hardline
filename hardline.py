#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# SPDX-FileCopyrightText: 2025 ArtificialSweetener <artificialsweetenerai@proton.me>
"""
ComfyUI Set/Get → Hardline (Tiny Tk GUI)
- Pick an input ComfyUI workflow JSON.
- Output defaults to "<input>_hardline.json" (you can override).
- Optional: drop Set/Get nodes after rewiring.

No external deps. Works with standard Python (tkinter).
"""

import json
from copy import deepcopy
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import sv_ttk
    _sv_ttk_available = True
except ImportError:
    _sv_ttk_available = False
import sys


class Tooltip:
    """Helper class to create tooltips for Tkinter widgets."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self._id = None # To store the after ID for cancelling
        self.delay = 750 # milliseconds
        self.widget.bind("<Enter>", self.schedule_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def schedule_tooltip(self, event=None):
        self.hide_tooltip() # Hide any existing tooltip or scheduled show
        self._id = self.widget.after(self.delay, self._show_tooltip_now)

    def _show_tooltip_now(self):
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20

        # Creates a toplevel window
        self.tooltip_window = tk.Toplevel(self.widget)
        # Hides the window border
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+%d+%d" % (x, y))

        label = tk.Label(self.tooltip_window,
                         text=self.text,
                         background="#333333", # Dark grey background
                         foreground="#FFFFFF", # White text
                         relief="solid",
                         borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        if self._id:
            self.widget.after_cancel(self._id)
            self._id = None
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None



# ---------------- Core conversion logic ----------------
def convert_setget_to_hardlines(workflow, drop_setget=False):
    """
    Rewire ComfyUI Set/Get to real links.

    For each SetNode, find its incoming link's origin (src_node, src_slot, type).
    For each GetNode with the same name, rewrite each outgoing link so the origin
    is (src_node, src_slot) and keep the link type consistent.

    Returns a new workflow dict and adds a summary at:
        extra.__hardline_rewire = {
            rewired_count, skipped_gets, conflicts
        }
    """
    wf = deepcopy(workflow)
    if 'nodes' not in wf or 'links' not in wf:
        raise ValueError("Input does not look like a ComfyUI workflow (missing 'nodes' or 'links').")

    nodes_by_id = {n['id']: n for n in wf['nodes']}
    # link: [id, from_node, from_slot, to_node, to_slot, type]
    link_map = {l[0]: l for l in wf['links']}

    def add_output_link(node_id, slot_index, link_id):
        node = nodes_by_id.get(node_id)
        if node is None:
            return
        outs = node.get('outputs', [])
        if not (0 <= slot_index < len(outs)):
            return
        if outs[slot_index].get('links') is None:
            outs[slot_index]['links'] = []
        if link_id not in outs[slot_index]['links']:
            outs[slot_index]['links'].append(link_id)

    def remove_output_link(node_id, slot_index, link_id):
        node = nodes_by_id.get(node_id)
        if node is None:
            return
        outs = node.get('outputs', [])
        if 0 <= slot_index < len(outs):
            links = outs[slot_index].get('links')
            if isinstance(links, list) and link_id in links:
                links.remove(link_id)

    # Build map: variable name -> (src_node_id, src_slot_index, link_type)
    name_to_source = {}
    conflicts = []
    for n in wf['nodes']:
        if n.get('type') == 'SetNode':
            name = (n.get('widgets_values') or [None])[0]
            if not name or not n.get('inputs'):
                continue
            inp = n['inputs'][0]
            link_id = inp.get('link')
            if link_id is None:
                continue
            link = link_map.get(link_id)
            if not link:
                continue
            _, src_node, src_slot, _, _, ltype = link
            candidate = (src_node, src_slot, ltype)
            prev = name_to_source.get(name)
            if prev and prev != candidate:
                conflicts.append((name, prev, candidate, n['id']))
            else:
                name_to_source[name] = candidate

    rewired = []
    skipped_gets = []

    for n in wf['nodes']:
        if n.get('type') == 'GetNode':
            name = (n.get('widgets_values') or [None])[0]
            if name not in name_to_source:
                skipped_gets.append((n['id'], name))
                continue
            src_node, src_slot, ltype = name_to_source[name]
            outs = n.get('outputs', [])
            for out_slot_index, out in enumerate(outs):
                link_ids = list(out.get('links') or [])
                for lid in link_ids:
                    link = link_map.get(lid)
                    if not link:
                        continue
                    # Rewrite origin to SetNode's upstream source
                    link[1] = src_node
                    link[2] = src_slot
                    link[5] = ltype
                    add_output_link(src_node, src_slot, lid)
                    remove_output_link(n['id'], out_slot_index, lid)
                    rewired.append((name, lid, n['id'], src_node))

    # Optionally drop Set/Get nodes and dangling links
    if drop_setget:
        new_nodes = []
        dropped_ids = set()
        for n in wf['nodes']:
            if n.get('type') in ('SetNode', 'GetNode'):
                dropped_ids.add(n['id'])
                continue
            new_nodes.append(n)
        wf['nodes'] = new_nodes

        keep_links = []
        for l in wf['links']:
            _, from_id, _, to_id, _, _ = l
            if from_id in dropped_ids or to_id in dropped_ids:
                continue
            keep_links.append(l)
        wf['links'] = keep_links

    wf.setdefault('extra', {}).setdefault('__hardline_rewire', {})['rewired_count'] = len(rewired)
    wf.setdefault('extra', {}).setdefault('__hardline_rewire', {})['skipped_gets'] = skipped_gets
    wf.setdefault('extra', {}).setdefault('__hardline_rewire', {})['conflicts'] = conflicts
    return wf


# ---------------------------- GUI ----------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        # Buffer early log messages until the log widget is ready
        pending_log_msgs = []

        # Theme: prefer sv-ttk dark if available; otherwise stock Tk/TTK
        use_dark_theme = False
        if _sv_ttk_available:
            sv_ttk.set_theme("dark")
            use_dark_theme = True
        else:
            # Quiet fallback: no in-app or console log
            pass
            pending_log_msgs.append("sv_ttk not found. Running with default Tkinter theme.")
        if use_dark_theme:
            self.configure(bg="#1c1c1c")
        self.title("ComfyUI Set/Get → Hardline")
        self.geometry("700x380")

        # Vars
        self.in_path_var = tk.StringVar()
        self.out_path_var = tk.StringVar()
        self.suffix_var = tk.StringVar(value="_hardline")
        self.drop_var = tk.BooleanVar(value=False)

        # Layout
        pad = {'padx': 8, 'pady': 6}
        frm = tk.Frame(self)
        frm.pack(fill="both", expand=True, **pad)
        if use_dark_theme:
            frm.configure(bg="#1c1c1c")

        # Input row
        row1 = ttk.Frame(frm); row1.pack(fill="x", **pad)
        ttk.Label(row1, text="Input JSON:").pack(side="left")
        in_entry = ttk.Entry(row1, textvariable=self.in_path_var)
        in_entry.pack(side="left", fill="x", expand=True, padx=6)
        Tooltip(in_entry, "Path to the input ComfyUI workflow JSON file.")
        ttk.Button(row1, text="Browse…", command=self.browse_input).pack(side="left")
        Tooltip(row1.winfo_children()[-1], "Browse for the input JSON file.")

        # Output row
        row2 = ttk.Frame(frm); row2.pack(fill="x", **pad)
        ttk.Label(row2, text="Output JSON:").pack(side="left")
        out_entry = ttk.Entry(row2, textvariable=self.out_path_var)
        out_entry.pack(side="left", fill="x", expand=True, padx=6)
        Tooltip(out_entry, "Path where the converted JSON file will be saved. Leave empty for default.")
        ttk.Button(row2, text="Save As…", command=self.choose_output).pack(side="left")
        Tooltip(row2.winfo_children()[-1], "Choose the output JSON file path.")

        # Options row
        row3 = ttk.Frame(frm); row3.pack(fill="x", **pad)
        ttk.Label(row3, text="Suffix (used if Output is empty):").pack(side="left")
        suffix_entry = ttk.Entry(row3, width=20, textvariable=self.suffix_var)
        suffix_entry.pack(side="left", padx=6)
        Tooltip(suffix_entry, "Suffix to add to the input filename for the default output filename.")
        drop_checkbox = ttk.Checkbutton(row3, text="Drop Set/Get nodes after rewiring", variable=self.drop_var)
        drop_checkbox.pack(side="left", padx=12)
        Tooltip(drop_checkbox, "If checked, Set/Get nodes will be removed from the workflow after conversion.")

        # Log box
        self.log = tk.Text(frm, height=10, wrap="word")
        if use_dark_theme:
            # Make log readable on the dark background
            self.log.configure(bg="#1e1e1e", fg="#e6e6e6", insertbackground="#e6e6e6")
        self.log.pack(fill="both", expand=True, **pad)
        self.log.config(state="disabled") # Make log read-only initially

        # Flush any pending log messages collected before log widget existed
        for _msg in pending_log_msgs:
            self.log_line(_msg)

        # Convert button row
        actions = ttk.Frame(frm); actions.pack(fill="x", **pad)
        self.convert_btn = ttk.Button(actions, text="Convert", command=self.convert)
        self.convert_btn.pack(side="left")
        Tooltip(self.convert_btn, "Start the conversion process.")
        quit_button = ttk.Button(actions, text="Quit", command=self.destroy)
        quit_button.pack(side="right")
        Tooltip(quit_button, "Exit the application.")

    # ---- helpers ----
    def log_line(self, s: str):
        self.log.config(state="normal")
        self.log.insert("end", s + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def default_output_path(self, in_path: Path) -> Path:
        suf = self.suffix_var.get() or "_hardline"
        return in_path.with_name(in_path.stem + suf + in_path.suffix)

    # ---- actions ----
    def browse_input(self):
        path = filedialog.askopenfilename(
            title="Select ComfyUI workflow JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        self.in_path_var.set(path)
        # Auto-suggest output when input changes
        self.out_path_var.set(str(self.default_output_path(Path(path))))

    def choose_output(self):
        path = filedialog.asksaveasfilename(
            title="Choose output JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            self.out_path_var.set(path)

    def convert(self):
        in_path = Path(self.in_path_var.get())
        out_path_str = self.out_path_var.get().strip()

        if not in_path.exists():
            messagebox.showerror("Error", "Please select a valid input JSON file.")
            return

        out_path = Path(out_path_str) if out_path_str else self.default_output_path(in_path)

        try:
            with in_path.open("r", encoding="utf-8") as f:
                wf = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read input JSON:\n{e}")
            return

        try:
            new_wf = convert_setget_to_hardlines(wf, drop_setget=self.drop_var.get())
        except Exception as e:
            messagebox.showerror("Error", f"Rewire failed:\n{e}")
            return

        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("w", encoding="utf-8") as f:
                json.dump(new_wf, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to write output JSON:\n{e}")
            return

        stats = new_wf.get("extra", {}).get("__hardline_rewire", {}) or {}
        msg = (
            f"Wrote: {out_path}\n"
            f"Rewired links: {stats.get('rewired_count')}\n"
            f"Skipped GetNodes: {len(stats.get('skipped_gets') or [])}\n"
            f"Conflicts: {len(stats.get('conflicts') or [])}\n"
        )
        self.log_line(msg)
        messagebox.showinfo("Done", msg)


if __name__ == "__main__":
    app = App()
    app.mainloop()
