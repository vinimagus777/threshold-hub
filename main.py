import flet as ft
import json
import os

SAVE_FILE = "campaign_save.json"

def main(page: ft.Page):
    page.title = "Threshold: Aleena's Heroes Grand Master Hub"
    page.theme_mode = ft.ThemeMode.DARK
    page.scroll = "adaptive"
    page.padding = 20
    page.window_width = 1100

    # --- 1. Persistent State ---
    state = {
        "pcs": [{"num": i+1, "name": f"Hero {i+1}", "class": "Fighter", "gender": "M", "ancestry": "Human", "maxHP": 10, "currHP": 10, "con_mod": 0, "effects": "None", "AC": 16, "currXP": 0, "nextXP": 2000} for i in range(12)],
        "vault": {"cp": 0, "sp": 0, "ep": 0, "gp": 0, "pp": 0, "items": [], "total_xp_pending": 0.0},
        "bargle_clues": 0,
        "last_taxed_baseline": 0.0,
        "tax_history": [],
        "monsters": []
    }

    def save_data():
        with open(SAVE_FILE, "w") as f:
            json.dump(state, f)
        page.snack_bar = ft.SnackBar(ft.Text("Campaign Saved"), duration=1000)
        page.snack_bar.open = True
        page.update()

    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            try: state.update(json.load(f))
            except: pass

    # --- 2. Logic Helpers ---
    def get_total_vault_val():
        v = state["vault"]
        coins = (v["cp"]*0.01) + (v["sp"]*0.1) + (v["ep"]*0.5) + v["gp"] + (v["pp"]*5)
        items = sum(item["val"] for item in v["items"])
        return coins + items

    # --- 3. UI Components ---
    party_grid = ft.ResponsiveRow(spacing=10)
    inventory_column = ft.Column(spacing=2)
    monster_list = ft.Column(spacing=5)
    coin_display = ft.Text(size=14, color="amber")
    xp_pending_text = ft.Text(size=20, weight="bold", color="lightgreen")
    clue_label = ft.Text(size=20, weight="bold")
    tax_proposal_log = ft.Column(spacing=2)
    backup_field = ft.TextField(label="Save Code Backup", multiline=True, min_lines=2, text_size=10)

    # --- 4. Core Features ---
    def handle_loot(e):
        try:
            val = float(l_val.value); mult = 12/7; adj = val * mult
            state["vault"]["total_xp_pending"] += adj
            if l_type.value in ["GP", "CP", "SP", "EP", "PP"]: 
                state["vault"][l_type.value.lower()] += adj
            else: 
                state["vault"]["items"].append({"desc": l_desc.value, "real_name": l_ident.value, "val": val, "is_magic": l_magic.value})
            save_data(); update_ui()
        except: pass

    def run_scrutiny(e):
        cur = get_total_vault_val()
        delta = max(0, cur - state["last_taxed_baseline"])
        if delta <= 0:
            tax_proposal_log.controls.clear()
            tax_proposal_log.controls.append(ft.Text("No new treasure since last audit.", color="green"))
            page.update(); return

        magic_val = sum(i["val"] for i in state["vault"]["items"] if i.get("is_magic"))
        ratio = magic_val / cur if cur > 0 else 0
        inc = (delta*(1-ratio)*0.21) + (delta*ratio*0.07)
        tithe = delta * 0.20; guild = delta * 0.10; total = inc + tithe + guild
        
        tax_proposal_log.controls.clear()
        tax_proposal_log.controls.append(ft.Text(f"DELTA: {delta:.2f}gp", weight="bold"))
        tax_proposal_log.controls.append(ft.Text(f"Taxes: {inc:.2f} | Tithe: {tithe:.2f} | Guild: {guild:.2f}"))
        tax_proposal_log.controls.append(ft.Text(f"TOTAL DUE: {total:.2f} gp", color="red", weight="bold"))
        pay_btn.data = total; pay_btn.visible = True; page.update()

    def confirm_pay(e):
        due = pay_btn.data; v = state["vault"]; rem = due
        for d in ["cp", "sp", "ep", "gp", "pp"]:
            rate = {"cp":0.01,"sp":0.1,"ep":0.5,"gp":1.0,"pp":5.0}[d]
            p = min(v[d]*rate, rem); v[d] -= (p/rate); rem -= p
        state["vault"]["total_xp_pending"] += (due * 0.25) # Karma Tax Bonus
        state["last_taxed_baseline"] = get_total_vault_val()
        pay_btn.visible = False; save_data(); update_ui()

    def donate_charity(e):
        try:
            amt = float(charity_amt.value)
            if state["vault"]["gp"] >= amt:
                state["vault"]["gp"] -= amt
                state["vault"]["total_xp_pending"] += (amt * 1.5) # Karma Altruism Bonus
                charity_amt.value = ""; save_data(); update_ui()
        except: pass

    def handle_monster_defeat(idx):
        adj_xp = state["monsters"][idx]["xp"] * (12/7)
        state["vault"]["total_xp_pending"] += adj_xp
        state["monsters"].pop(idx); save_data(); update_ui()

    # --- 5. UI Refresh ---
    def update_ui():
        page.bgcolor = "#330000" if state["bargle_clues"] >= 10 else None
        clue_label.value = f"Bargle Clues: {state['bargle_clues']}/10"
        xp_pending_text.value = f"Party XP Pending: {state['vault']['total_xp_pending']:.2f}"
        coin_display.value = f"💰 {state['vault']['cp']:.0f}cp | {state['vault']['sp']:.0f}sp | {state['vault']['gp']:.0f}gp | {state['vault']['pp']:.0f}pp"
        
        inventory_column.controls.clear()
        for i in state["vault"]["items"]:
            m = " [M]" if i.get("is_magic") else ""
            inventory_column.controls.append(ft.Row([ft.Text(f"P: {i['desc']}", color="cyan", size=11), ft.Text(f"DM: {i['real_name']}{m}", color="orange", italic=True, size=11)]))
        
        monster_list.controls.clear()
        for i, m in enumerate(state["monsters"]):
            monster_list.controls.append(ft.Container(content=ft.Row([ft.Text(f"{m['name']} (HP:{m['hp']})", expand=True), ft.IconButton(ft.icons.REMOVE, on_click=lambda _, idx=i: [setitem(state['monsters'][idx], 'hp', state['monsters'][idx]['hp']-1), save_data(), update_ui()]), ft.IconButton(ft.icons.CHECK, on_click=lambda _, idx=i: handle_monster_defeat(idx))]), border=ft.border.all(1, "red"), padding=5))
            
        party_grid.controls.clear()
        for i, pc in enumerate(state["pcs"]):
            party_grid.controls.append(ft.Container(content=ft.Column([ft.TextButton(f"#{pc['num']} {pc['name']}", on_click=lambda _, idx=i: open_editor(idx)), ft.Text(f"HP: {pc['currHP']}/{pc['maxHP']} | XP: {pc['currXP']:.0f}", size=12), ft.Text(f"FX: {pc['effects']}", size=10, italic=True, color="yellow")]), padding=10, border=ft.border.all(1, "grey"), border_radius=8, col={"sm": 12, "md": 6, "lg": 4}))
        page.update()

    # --- 6. Modal Editor ---
    e_name = ft.TextField(label="Name"); e_hp = ft.TextField(label="HP"); e_con = ft.TextField(label="CON"); e_fx = ft.TextField(label="Effects")
    editing_idx = None
    def open_editor(idx):
        nonlocal editing_idx; editing_idx = idx; p = state["pcs"][idx]
        e_name.value = p["name"]; e_hp.value = str(p["currHP"]); e_con.value = str(p.get("con_mod", 0)); e_fx.value = p["effects"]
        dlg.open = True; page.update()
    def save_editor(e):
        p = state["pcs"][editing_idx]; p.update({"name":e_name.value, "currHP":int(e_hp.value), "con_mod":int(e_con.value), "effects":e_fx.value}); dlg.open = False; save_data(); update_ui()
    dlg = ft.AlertDialog(title=ft.Text("Edit Hero"), content=ft.Column([e_name,e_hp,e_con,e_fx], tight=True), actions=[ft.TextButton("Save", on_click=save_editor)])
    page.overlay.append(dlg)

    # --- 7. Layout Widgets ---
    l_type = ft.Dropdown(label="Type", options=[ft.dropdown.Option(x) for x in ["GP","CP","SP","Gem","Art","Magic"]], value="GP", width=90)
    l_desc = ft.TextField(label="Player Info", expand=True); l_ident = ft.TextField(label="DM Info", expand=True)
    l_val = ft.TextField(label="Value", width=80); l_magic = ft.Checkbox(label="Magic?", value=False)
    m_n = ft.TextField(label="Monster", expand=True); m_h = ft.TextField(label="HP", width=60); m_x = ft.TextField(label="Base XP", width=80)
    charity_amt = ft.TextField(label="Donation (gp)", width=120)
    pay_btn = ft.ElevatedButton("CONFIRM TAX PAYMENT", on_click=confirm_pay, visible=False, bgcolor="green")
    initial_val = ft.TextField(label="Starting Wealth", width=150)

    def setitem(d, k, v): d[k] = v # Helper for lambda

    page.add(
        ft.Row([ft.Text("THRESHOLD HUB: GRAND MASTER", size=26, weight="bold"), clue_label], alignment="spaceBetween"),
        ft.Row([coin_display, xp_pending_text]),
        ft.Divider(),
        ft.Text("LOOT ENTRY", weight="bold", color="amber"),
        ft.Row([l_type, l_desc, l_ident, l_val, l_magic, ft.IconButton(ft.icons.ADD, on_click=handle_loot)]),
        ft.Divider(),
        ft.Text("BATTLEFIELD", weight="bold", color="red"),
        ft.Row([m_n, m_h, m_x, ft.ElevatedButton("Add Enemy", on_click=lambda _: [state["monsters"].append({"name":m_n.value, "hp":int(m_h.value), "xp":int(m_x.value)}), save_data(), update_ui()])]),
        ft.Row([ft.Column([monster_list], expand=1), ft.VerticalDivider(), ft.Column([ft.Text("The Party", size=20), party_grid], expand=2)], vertical_alignment="start"),
        ft.Divider(),
        ft.Row([
            ft.ElevatedButton("Level Up (1/12)", icon=ft.icons.UPGRADE, on_click=lambda _: [setattr(pc, 'currXP', pc['currXP']+(state['vault']['total_xp_pending']/12)) for pc in state["pcs"]] or state.update({"vault":{"total_xp_pending":0}}) or save_data() or update_ui()),
            ft.ElevatedButton("🏠 Rest at Inn", on_click=lambda _: [pc.update({"currHP":min(pc["maxHP"], pc["currHP"]+max(2,2+pc["con_mod"])), "effects":"None"}) for pc in state["pcs"]] or save_data() or update_ui(), color="green"),
            ft.ElevatedButton("Bargle Clue", on_click=lambda _: [state.update({"bargle_clues": state["bargle_clues"]+1}), save_data(), update_ui()], color="orange"),
        ]),
        ft.Divider(),
        ft.Row([
            ft.Column([
                ft.Text("Town Hall & Charity", size=18, weight="bold"),
                ft.Row([initial_val, ft.ElevatedButton("Set Starting Wealth", on_click=lambda _: [state.update({"last_taxed_baseline":float(initial_val.value)}), save_data(), update_ui()])]),
                ft.ElevatedButton("📄 Generate Tax Invoice", on_click=run_scrutiny),
                tax_proposal_log, pay_btn,
                ft.Row([charity_amt, ft.ElevatedButton("Donate GP", on_click=donate_charity)]),
                ft.Text("Inventory Log", size=18, weight="bold"), inventory_column
            ], expand=1),
            ft.VerticalDivider(),
            ft.Column([
                ft.Text("Backup Management", size=18, weight="bold"),
                ft.Row([ft.ElevatedButton("Export", on_click=lambda e: [setattr(backup_field, 'value', json.dumps(state)), page.set_clipboard(backup_field.value), page.update()]), ft.ElevatedButton("Import", on_click=lambda e: [state.update(json.loads(backup_field.value)), save_data(), update_ui()])]),
                backup_field
            ], expand=1)
        ])
    )
    update_ui()

ft.app(target=main)
