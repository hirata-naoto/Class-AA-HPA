diff --git a/root/gen_classaa.py b/root/gen_classaa.py
create file mode 100644
index 0000000..0000000
--- a/dev/null
+++ b/root/gen_classaa.py
@@ -1,0 +1,191 @@
+#!/usr/bin/env python3
+"""ClassAA ヘッドホンアンプ回路から KiCad 7 の .kicad_sch を生成する。
+
+部品は同梱の簡易シンボル(Local:*)を使い、接続はピン端のネットラベルで表現する。
+使い方: python3 gen_classaa.py [出力.kicad_sch]
+生成後、KiCad で開き必要なら標準ライブラリのシンボルに差し替えてください。
+"""
+import sys
+import uuid
+
+def uid():
+    return str(uuid.uuid4())
+
+FONT = "(effects (font (size 1.27 1.27)))"
+
+# ---- シンボル定義: pins = (番号, 名前, x, y, 角度) 座標はシンボル座標系(Y上向き)
+# 角度: 0=右向き(ピンは左側), 180=左向き(右側), 90=上向き(下側), 270=下向き(上側)
+LIB = {
+    "R": dict(body=(-1.016, -2.54, 1.016, 2.54),
+              pins=[("1", "~", 0, 3.81, 270), ("2", "~", 0, -3.81, 90)]),
+    "C": dict(body=(-1.27, -0.6, 1.27, 0.6),
+              pins=[("1", "~", 0, 3.81, 270), ("2", "~", 0, -3.81, 90)]),
+    "D": dict(body=(-1.27, -1.27, 1.27, 1.27),
+              pins=[("1", "A", 0, 3.81, 270), ("2", "K", 0, -3.81, 90)]),
+    "POT": dict(body=(-1.016, -2.54, 1.016, 2.54),
+                pins=[("1", "1", 0, 3.81, 270), ("2", "2", 0, -3.81, 90),
+                      ("3", "W", -3.81, 0, 0)]),
+    "Q_NPN": dict(body=(-2.54, -2.54, 2.54, 2.54),
+                  pins=[("C", "C", 2.54, 5.08, 270), ("B", "B", -5.08, 0, 0),
+                        ("E", "E", 2.54, -5.08, 90)]),
+    "Q_PNP": dict(body=(-2.54, -2.54, 2.54, 2.54),
+                  pins=[("C", "C", 2.54, -5.08, 90), ("B", "B", -5.08, 0, 0),
+                        ("E", "E", 2.54, 5.08, 270)]),
+    "Q_NJFET": dict(body=(-2.54, -2.54, 2.54, 2.54),
+                    pins=[("D", "D", 2.54, 5.08, 270), ("G", "G", -5.08, 0, 0),
+                          ("S", "S", 2.54, -5.08, 90)]),
+    # LME49720NA: unit1=amp A(3,2,1) unit2=amp B(5,6,7) unit3=電源(8,4)
+    "LME49720NA": dict(
+        units={
+            1: dict(body=(-5.08, -5.08, 5.08, 5.08),
+                    pins=[("3", "+", -7.62, 2.54, 0), ("2", "-", -7.62, -2.54, 0),
+                          ("1", "~", 7.62, 0, 180)]),
+            2: dict(body=(-5.08, -5.08, 5.08, 5.08),
+                    pins=[("5", "+", -7.62, 2.54, 0), ("6", "-", -7.62, -2.54, 0),
+                          ("7", "~", 7.62, 0, 180)]),
+            3: dict(body=(-5.08, -5.08, 5.08, 5.08),
+                    pins=[("8", "V+", 0, 7.62, 270), ("4", "V-", 0, -7.62, 90)]),
+        }),
+}
+
+def units_of(name):
+    d = LIB[name]
+    return d["units"] if "units" in d else {1: d}
+
+def lib_symbol_sexp(name):
+    out = [f'(symbol "Local:{name}" (pin_names (offset 0.5)) (in_bom yes) (on_board yes)',
+           f'(property "Reference" "{"U" if name.startswith("LME") else name[0]}" (at 0 0 0) {FONT})',
+           f'(property "Value" "{name}" (at 0 0 0) {FONT})',
+           '(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
+           '(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))']
+    for u, d in units_of(name).items():
+        x1, y1, x2, y2 = d["body"]
+        out.append(f'(symbol "{name}_{u}_1"')
+        out.append(f'(rectangle (start {x1} {y1}) (end {x2} {y2}) '
+                   '(stroke (width 0.254) (type default)) (fill (type background)))')
+        for num, pname, x, y, a in d["pins"]:
+            out.append(f'(pin passive line (at {x} {y} {a}) (length 2.54) '
+                       f'(name "{pname}" {FONT}) (number "{num}" {FONT}))')
+        out.append(')')
+    out.append(')')
+    return "\n".join(out)
+
+def label_angle(a):
+    # ピン向き -> ラベル向き
+    return {0: 180, 180: 0, 90: 270, 270: 90}[a]
+
+class Sch:
+    def __init__(self):
+        self.items = []
+        self.used = set()
+
+    def part(self, ref, value, lib, x, y, nets, unit=1):
+        """nets: {ピン番号: ネット名}"""
+        d = units_of(lib)[unit]
+        s = [f'(symbol (lib_id "Local:{lib}") (at {x} {y} 0) (unit {unit}) '
+             f'(in_bom yes) (on_board yes) (dnp no) (uuid {uid()})',
+             f'(property "Reference" "{ref}" (at {x + 3} {y - 2} 0) {FONT})',
+             f'(property "Value" "{value}" (at {x + 3} {y + 2} 0) {FONT})',
+             '(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
+             '(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))']
+        for num, *_ in d["pins"]:
+            s.append(f'(pin "{num}" (uuid {uid()}))')
+        s.append(f'(instances (project "classaa" (path "/{ROOT}" '
+                 f'(reference "{ref}") (unit {unit}))))')
+        s.append(')')
+        self.items.append("\n".join(s))
+        for num, _n, px, py, a in d["pins"]:
+            net = nets.get(num)
+            if not net:
+                continue
+            lx, ly = round(x + px, 2), round(y - py, 2)
+            self.items.append(
+                f'(label "{net}" (at {lx} {ly} {label_angle(a)}) '
+                f'(effects (font (size 1.27 1.27)) (justify left bottom)) (uuid {uid()}))')
+
+    def text(self, s, x, y):
+        self.items.append(f'(text "{s}" (at {x} {y} 0) {FONT} (uuid {uid()}))')
+
+ROOT = uid()
+
+def channel(sch, ch, ox, oy, first_unit, boost_unit, ref_u, ref_prefix):
+    """ch: 'R' or 'L'。ネット名は ch 接頭辞で分離。"""
+    n = lambda s: f"{ch}_{s}"
+    P = []  # (種別, ref, value, lib, nets)
+    r = lambda ref, val, a, b: P.append((f"{ref_prefix}{ref}", val, "R", {"1": a, "2": b}))
+    # 入力: 10k(Aカーブ) ボリューム + 16k + 24k
+    P.append((f"RV{ref_u}", "10k(A)", "POT", {"1": f"{ch}in", "2": "GND", "3": n("W")}))
+    r("R1", "16k", n("W"), "GND")
+    r("R2", "24k", n("FBN"), "GND")
+    # 帰還: 47k // 4.7p を ROUTN へ
+    r("R3", "47k", n("FBN"), n("ROUTN"))
+    P.append((f"C{ref_u}1", "4.7p", "C", {"1": n("FBN"), "2": n("ROUTN")}))
+    # ブリッジ抵抗 (3.3k,33,1k,10) と出力 2.2
+    r("R4", "3.3k", n("M"), n("A"))
+    r("R5", "33", n("M"), n("OPOUT"))
+    r("R6", "1k", n("A"), n("ROUTN"))
+    r("R7", "10", n("OPOUT"), n("ROUTN"))
+    r("R8", "2.2", n("ROUTN"), f"{ch}out")
+    # エミッタ抵抗 2.2 x2
+    r("R9", "2.2", n("EN"), n("M"))
+    r("R10", "2.2", n("EP"), n("M"))
+    # トランジスタ・JFET・ダイオード
+    P.append((f"Q{ref_u}1", "2SC2120", "Q_NPN", {"C": "Vcc", "B": n("NA"), "E": n("EN")}))
+    P.append((f"Q{ref_u}2", "2SA950", "Q_PNP", {"C": "Vee", "B": n("NB"), "E": n("EP")}))
+    P.append((f"Q{ref_u}3", "2SK246", "Q_NJFET", {"D": "Vcc", "G": n("NA"), "S": n("NA")}))
+    P.append((f"Q{ref_u}4", "2SK246", "Q_NJFET", {"D": "Vee", "G": n("NB"), "S": n("NB")}))
+    P.append((f"D{ref_u}1", "1N4148", "D", {"1": n("NA"), "2": n("X")}))
+    P.append((f"D{ref_u}2", "1N4148", "D", {"1": n("X"), "2": n("NB")}))
+    # 配置 (グリッド)
+    for i, (ref, val, lib, nets) in enumerate(P):
+        x = ox + (i % 8) * 38
+        y = oy + (i // 8) * 30
+        sch.part(ref, val, lib, round(x / 1.27) * 1.27, round(y / 1.27) * 1.27, nets)
+    # オペアンプ: 初段(OPOUT出力) / ブースタ(X出力)
+    ay = oy + 75
+    u = f"U{ref_u}"
+    def amp(unit, plus, minus, out, x):
+        sch.part(u, "LME49720NA", "LME49720NA", x, ay, {
+            ("5" if unit == 2 else "3"): plus,
+            ("6" if unit == 2 else "2"): minus,
+            ("7" if unit == 2 else "1"): out}, unit=unit)
+    amp(first_unit, n("W"), n("FBN"), n("OPOUT"), ox + 20)
+    amp(boost_unit, n("OPOUT"), n("A"), n("X"), ox + 60)
+    sch.part(u, "LME49720NA", "LME49720NA", ox + 100, ay,
+             {"8": f"{ch}pV", "4": f"{ch}pN"}, unit=3)
+    # 電源デカップリング 0.1u x2
+    sch.part(f"C{ref_u}2", "0.1u", "C", ox + 130, ay, {"1": f"{ch}pV", "2": "GND"})
+    sch.part(f"C{ref_u}3", "0.1u", "C", ox + 150, ay, {"1": "GND", "2": f"{ch}pN"})
+    # ※ U の V+/V- は Vcc/Vee に接続 (ネットタイ、0Ω扱いの別ラベルを避けるため同名で代用)
+    sch.items.append(
+        f'(label "{ch}pV" (at {ox + 100} {ay - 12} 90) (effects (font (size 1.27 1.27))) (uuid {uid()}))')
+
+
+def main():
+    out = sys.argv[1] if len(sys.argv) > 1 else "classaa.kicad_sch"
+    sch = Sch()
+    sch.text("10, 33, 1k, 3.3k, 24k, 47k は誤差1%品を使用 (前4つ: Wブリッジ, 後2つ: 負帰還/接地)", 20, 15)
+    sch.text("左右でオペアンプのPin番号が違うのはレイアウト都合で、電気的特性は同じ", 20, 22)
+    # 電源部
+    sch.part("R100", "22", "R", 30, 40, {"1": "+V_IN", "2": "Vcc"})
+    sch.part("R101", "22", "R", 60, 40, {"1": "-V_IN", "2": "Vee"})
+    sch.part("C100", "1000u", "C", 90, 40, {"1": "Vcc", "2": "GND"})
+    sch.part("C101", "1000u", "C", 110, 40, {"1": "GND", "2": "Vee"})
+    # 右 (U1: 初段=unit2(5,6,7), ブースタ=unit1(3,2,1)) / 左 (U2: 初段=unit1, ブースタ=unit2)
+    channel(sch, "R", 20, 60, first_unit=2, boost_unit=1, ref_u=1, ref_prefix="")
+    channel(sch, "L", 20, 190, first_unit=1, boost_unit=2, ref_u=2, ref_prefix="")
+    # 各チャネルの V+/V- を Vcc/Vee へ (ネット名の別名が必要なため0Ωで接続)
+    for i, ch in enumerate("RL"):
+        sch.part(f"R{200 + i * 2}", "0", "R", 300, 60 + i * 30, {"1": f"{ch}pV", "2": "Vcc"})
+        sch.part(f"R{201 + i * 2}", "0", "R", 320, 60 + i * 30, {"1": f"{ch}pN", "2": "Vee"})
+
+    libs = "\n".join(lib_symbol_sexp(n) for n in LIB)
+    body = "\n".join(sch.items)
+    with open(out, "w", encoding="utf-8") as f:
+        f.write(f'(kicad_sch (version 20230121) (generator classaa_gen)\n'
+                f'(uuid {ROOT})\n(paper "A2")\n(lib_symbols\n{libs}\n)\n{body}\n'
+                f'(sheet_instances (path "/" (page "1")))\n)\n')
+    print("wrote", out)
+
+if __name__ == "__main__":
+    main()
