# VEIL Guardian for Open WebUI

A paste-in filter that makes a home [Open WebUI](https://openwebui.com) install honour a **VEIL v1.2 Tier G (Guardian) envelope** for a child's account. No terminal, no build step: a parent copies one file into the Admin Panel.

What it does on every message from the child's account:

- Locks the content ceilings to the child's age profile (`VEIL-U13`, `VEIL-13` or `VEIL-16`). A guardian can lower a ceiling in the envelope; the filter clamps anything higher back down.
- Puts the VEIL session block and the six **minor-profile engine obligations** in front of the model: no sexual content, crisis handling, no companion framing, no secrecy from the parent, logging, AI disclosure.
- Scans for crisis language and, on a hit, tells the model to set the task aside and give the jurisdiction's help lines (AU, NZ, UK, US, CA built in).
- Writes a one-line audit record per turn to a log the guardian can read. The full transcript is still in Admin Panel → Users, as always.
- Fails closed: if the envelope is missing or invalid, the child's messages are blocked with a message to ask the parent, until it is fixed.
- Leaves admin accounts untouched.

It is a reference implementation. It does not replace the model's own safety training; it sits on top of it, which is the VEIL rule.

## Install (parent, about five minutes)

**1. Open the file**
Open [`veil_guardian.py`](./veil_guardian.py) on GitHub, click **Raw**, select all, copy.

**2. Add the function**
In Open WebUI, signed in as the admin: **Admin Panel → Functions → + (New Function)**. Paste the file over the editor contents. Click **Save**. Older versions: **Workspace → Functions**.

**3. Turn it on everywhere**
On the new *VEIL Guardian (Tier G)* row, switch it **on**, then open the **⋮** menu and switch **Global** on, so it applies to every model.

**4. Fill in the envelope**
On the same row, click the **⚙ Valves** icon. In **envelope_json**:
- change `creator_id` to the **child's Open WebUI email** (the one you created for them)
- change `guardian.creator_id` to **your** email
- set `minor_profile` to `VEIL-U13`, `VEIL-13` or `VEIL-16`
- change `context_id` to anything you like (`home-2026-01`)
- lower any ceiling you want lower; you cannot raise one above the profile

Set **guardian_label** to what the child calls you ("Mum", "Dad"). Save.

**5. Test it**
Sign in as the child and ask anything. A small status line *VEIL Tier G · VEIL-16 · envelope …* should appear on the reply. Ask "is this conversation private?" and the model should tell them it is logged and visible to you.

## Reading the log

The transcript: **Admin Panel → Users → (child) → Chats**.

The audit log (one JSON line per turn, with the envelope ID, a 200-character preview and a crisis flag): the file named in the **log_file** valve, by default `veil-guardian.jsonl` inside Open WebUI's data folder. With the Docker install from the guide, that is the `open-webui` volume. Set the valve to a path you can reach, or blank it to switch the file off; the transcript in the Admin Panel does not depend on it.

## Valves

| Valve | Default | What it does |
|---|---|---|
| `envelope_json` | sample Tier G envelope | The envelope. Must be tier G with a valid `minor_profile`. |
| `apply_to` | `creator_id` | `creator_id` = only the account whose email matches the envelope. `all_users` = every non-admin account. |
| `guardian_label` | `a parent or guardian` | How the model refers to you. |
| `purpose` | `study, research and creative work` | One line in the system prompt. |
| `crisis_scan` | on | Keyword scan that moves obligation 2 to the front on that turn. |
| `log_file` | `/app/backend/data/veil-guardian.jsonl` | Audit log path; blank to disable. |
| `show_status` | on | Status line on each reply. |
| `fail_closed` | on | Block the child if the envelope is invalid. |

## Limits

- The ceilings are enforced by instruction to the model, not by a content classifier. A capable local model honours them well; a small one honours them less well. The transcript is the backstop, which is the point of Tier G.
- The crisis scan is a plain keyword list in English. It is there to make sure obligation 2 is in front of the model on the turns that matter, not to diagnose anything.
- Only Open WebUI is covered here. The same envelope and block work with any engine that accepts a system prompt; see the standard's *Session Context Block*.

## Licence

CC BY-SA 4.0, like the standard. The VEIL certification badge and the R8rly mark remain protected.
