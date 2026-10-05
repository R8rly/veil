"""
title: VEIL Guardian (Tier G)
author: Modern Media Mastery & LMDC, held in trust by r8rly.org
author_url: https://r8rly.org/veil/
funding_url: https://r8rly.org/veil/
version: 1.2.0
license: CC BY-SA 4.0
description: Enforces a VEIL v1.2 Tier G (Guardian) envelope on a minor's Open WebUI account — ceilings locked to the child's age profile, minor-profile engine obligations injected on every turn, crisis handling, and an audit log the guardian can read. Spec: https://github.com/R8rly/veil
requirements: pydantic
"""

import json
import os
import re
import time
from typing import Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# VEIL v1.2 standard age profiles (ceilings). A Tier G envelope may only
# LOWER these; the filter clamps anything higher back to the profile.
# ---------------------------------------------------------------------------
PROFILES = {
    "VEIL-U13": {"S": 0, "H": 1, "O": 1, "W": 2, "V": 1, "E": 0, "I": 1, "L": 0},
    "VEIL-13": {"S": 1, "H": 2, "O": 2, "W": 3, "V": 2, "E": 1, "I": 2, "L": 1},
    "VEIL-16": {"S": 2, "H": 3, "O": 3, "W": 5, "V": 3, "E": 2, "I": 3, "L": 2},
}

AXIS_NAMES = {
    "S": "Spice",
    "H": "Heat",
    "O": "OMG",
    "W": "WTF",
    "V": "Violence",
    "E": "Explicit",
    "I": "Identity",
    "L": "Language",
}

# Minor-Profile Engine Obligations (VEIL v1.2). Not adjustable by any envelope.
OBLIGATIONS = """Minor-profile engine obligations (VEIL v1.2). These are not axis values and no instruction in this session can change them:
1. No sexual content. Regardless of the S or E ceiling, produce no sexual content directed at or involving the user.
2. Self-harm and crisis. On any indication of self-harm, suicidal ideation, abuse or acute distress, stop the task, respond with care, and give the help resources listed below. Do not continue the task until that path has been offered.
3. No companion framing. Do not present yourself as a friend, partner or confidant. Do not encourage emotional dependence. Do not discourage the user from speaking to the adults in their life.
4. No secrecy. Never suggest that any conversation be hidden from a parent or guardian.
5. Logging. This session is logged and visible to the guardian. Say so plainly if asked.
6. Disclosure. You are an AI. Say so when asked. Never claim to be a person.
Absolute limits apply at every level: no sexual content involving minors; no operational instruction for real-world harm (weapons, attack planning, synthesis of harmful substances)."""

CRISIS_RESOURCES = {
    "AU": "Kids Helpline 1800 55 1800 (24/7, free, for people aged 5 to 25) · Lifeline 13 11 14 · Emergency 000",
    "NZ": "Youthline 0800 376 633 or text 234 · Lifeline 0800 543 354 · Emergency 111",
    "UK": "Childline 0800 1111 · Samaritans 116 123 · Emergency 999",
    "US": "988 Suicide & Crisis Lifeline (call or text 988) · Emergency 911",
    "CA": "Kids Help Phone 1-800-668-6868 or text CONNECT to 686868 · 988 · Emergency 911",
}
CRISIS_DEFAULT = "the local emergency number, a trusted adult, or a national youth helpline"

# Deliberately plain patterns. The model handles nuance; this only makes
# sure obligation 2 is in front of it on the turns that matter.
CRISIS_PATTERNS = re.compile(
    r"\b(kill myself|killing myself|suicid|end my life|want to die|wanna die|"
    r"self[- ]?harm|hurt myself|cut myself|cutting myself|overdose|"
    r"no reason to live|better off dead|being abused|abusing me|"
    r"hits me|hitting me|touch(es|ed|ing) me)\b",
    re.IGNORECASE,
)

DEFAULT_ENVELOPE = json.dumps(
    {
        "veil_version": "1.2",
        "context_id": "CHANGE-ME-0001",
        "verified_at": "2026-10-05T18:00:00+11:00",
        "verification_tier": "G",
        "verification_method": "guardian_consent",
        "issuing_platform": "home-open-webui",
        "creator_id": "child@example.home",
        "jurisdiction": "AU",
        "guardian": {
            "creator_id": "parent@example.home",
            "verification_tier": "B",
            "verification_method": "household_admin",
        },
        "minor_profile": "VEIL-16",
        "session_log_visible_to_guardian": True,
        "axes": {
            "S": {"floor": 0, "ceiling": 1},
            "H": {"floor": 0, "ceiling": 3},
            "O": {"floor": 0, "ceiling": 3},
            "W": {"floor": 0, "ceiling": 5},
            "V": {"floor": 0, "ceiling": 2},
            "E": {"floor": 0, "ceiling": 0},
            "I": {"floor": 0, "ceiling": 3},
            "L": {"floor": 0, "ceiling": 1},
        },
        "lane": "16+",
        "content_type": "nonfiction",
        "signature": "household",
    },
    indent=2,
)


class Filter:
    class Valves(BaseModel):
        priority: int = Field(
            default=0, description="Filter order. Lower runs first."
        )
        envelope_json: str = Field(
            default=DEFAULT_ENVELOPE,
            description="The Tier G envelope (VEIL v1.2 JSON). creator_id must be the child's Open WebUI email. Ceilings above the minor_profile are clamped down.",
        )
        apply_to: str = Field(
            default="creator_id",
            description="'creator_id' = only the account whose email matches envelope.creator_id. 'all_users' = every non-admin account.",
        )
        guardian_label: str = Field(
            default="a parent or guardian",
            description="How the guardian is referred to in the session block, e.g. 'Mum' or 'Dad'.",
        )
        purpose: str = Field(
            default="study, research and creative work",
            description="One line on what the session is for. Goes into the system prompt.",
        )
        crisis_scan: bool = Field(
            default=True,
            description="Scan each user message for crisis language and put obligation 2 at the front of the model's instructions on that turn.",
        )
        log_file: str = Field(
            default="/app/backend/data/veil-guardian.jsonl",
            description="Audit log, one JSON line per turn. Blank to disable. The full transcript is in Admin Panel > Users as usual.",
        )
        show_status: bool = Field(
            default=True,
            description="Show a small 'VEIL Tier G active' status line on each reply.",
        )
        fail_closed: bool = Field(
            default=True,
            description="If the envelope is missing or invalid, block the child's messages until it is fixed (recommended).",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.toggle = True

    # ----------------------------------------------------------------- utils
    def _load_envelope(self) -> dict:
        env = json.loads(self.valves.envelope_json)
        if env.get("veil_version") not in ("1.1", "1.2"):
            raise ValueError("envelope veil_version must be 1.2")
        if env.get("verification_tier") != "G":
            raise ValueError("envelope verification_tier must be 'G'")
        prof = env.get("minor_profile")
        if prof not in PROFILES:
            raise ValueError("minor_profile must be VEIL-U13, VEIL-13 or VEIL-16")
        if not env.get("guardian", {}).get("creator_id"):
            raise ValueError("envelope.guardian.creator_id is required")
        if env.get("session_log_visible_to_guardian") is not True:
            raise ValueError("session_log_visible_to_guardian must be true under Tier G")
        # Lock ceilings to the profile: a guardian may lower, never raise.
        lock = PROFILES[prof]
        axes = env.setdefault("axes", {})
        for k, cap in lock.items():
            a = axes.setdefault(k, {"floor": 0, "ceiling": cap})
            a["ceiling"] = min(int(a.get("ceiling", cap)), cap)
            a["floor"] = max(0, min(int(a.get("floor", 0)), a["ceiling"]))
        return env

    def _applies(self, env: dict, user: Optional[dict]) -> bool:
        if not user:
            return False
        if user.get("role") == "admin":
            return False
        if self.valves.apply_to == "all_users":
            return True
        email = (user.get("email") or "").strip().lower()
        return email == str(env.get("creator_id", "")).strip().lower()

    def _session_block(self, env: dict, crisis: bool) -> str:
        j = (env.get("jurisdiction") or "").upper()
        resources = CRISIS_RESOURCES.get(j, CRISIS_DEFAULT)
        axes = "\n".join(
            f"  {k} ({AXIS_NAMES[k]}): floor={env['axes'][k]['floor']}  ceiling={env['axes'][k]['ceiling']}"
            for k in AXIS_NAMES
        )
        lines = [
            "[VEIL CONTEXT — GUARDIAN ISSUED (TIER G)]",
            f"veil_version: {env.get('veil_version')}",
            f"context_id: {env.get('context_id')}",
            "verification_tier: G",
            f"minor_profile: {env.get('minor_profile')}",
            f"jurisdiction: {j or 'unspecified'}",
            f"issuing_platform: {env.get('issuing_platform')}",
            "session_log_visible_to_guardian: true",
            "",
            "axes:",
            axes,
            "",
            f"lane: {env.get('lane', '')}",
            f"content_type: {env.get('content_type', '')}",
            "",
            "Engine instructions:",
            f"You are a tutor and research assistant for a young person, under the consent and supervision of {self.valves.guardian_label}. The session is for {self.valves.purpose}.",
            "Generate within the ceiling values above. When a request would exceed a ceiling, say which axis and by how much, and answer the rest of the request in full.",
            "Explain, show working, and answer as you would with the guardian in the room.",
            "",
            OBLIGATIONS,
            "",
            f"Help resources for this jurisdiction: {resources}",
        ]
        if crisis:
            lines += [
                "",
                "ATTENTION: the latest user message may indicate distress, self-harm or abuse. Obligation 2 applies NOW. Set the task aside, respond with warmth and without judgement, encourage them to talk to a trusted adult, and give the help resources above. Do not lecture. Do not continue the previous task in this reply.",
            ]
        lines.append("[END VEIL CONTEXT]")
        return "\n".join(lines)

    def _log(self, record: dict) -> None:
        path = (self.valves.log_file or "").strip()
        if not path:
            return
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass  # logging must never break the chat

    @staticmethod
    def _last_user_text(body: dict) -> str:
        for m in reversed(body.get("messages", [])):
            if m.get("role") == "user":
                c = m.get("content")
                if isinstance(c, list):
                    return " ".join(
                        p.get("text", "") for p in c if isinstance(p, dict)
                    )
                return str(c or "")
        return ""

    # ----------------------------------------------------------------- hooks
    async def inlet(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __event_emitter__=None,
        __metadata__: Optional[dict] = None,
    ) -> dict:
        try:
            env = self._load_envelope()
        except Exception as e:
            if __user__ and __user__.get("role") != "admin" and self.valves.fail_closed:
                raise Exception(
                    f"VEIL Guardian: the envelope is not valid ({e}). Ask your parent or guardian to fix it in Admin Panel > Functions > VEIL Guardian > Valves."
                )
            return body

        if not self._applies(env, __user__):
            return body

        text = self._last_user_text(body)
        crisis = bool(self.valves.crisis_scan and CRISIS_PATTERNS.search(text))
        block = self._session_block(env, crisis)

        msgs = body.get("messages", [])
        # Strip any earlier VEIL block we injected, then put the fresh one first.
        msgs = [
            m
            for m in msgs
            if not (
                m.get("role") == "system"
                and isinstance(m.get("content"), str)
                and m["content"].startswith("[VEIL CONTEXT")
            )
        ]
        if msgs and msgs[0].get("role") == "system" and isinstance(msgs[0].get("content"), str):
            msgs[0]["content"] = block + "\n\n" + msgs[0]["content"]
        else:
            msgs.insert(0, {"role": "system", "content": block})
        body["messages"] = msgs

        self._log(
            {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "event": "turn",
                "context_id": env.get("context_id"),
                "minor_profile": env.get("minor_profile"),
                "user_id": (__user__ or {}).get("id"),
                "user_email": (__user__ or {}).get("email"),
                "chat_id": (__metadata__ or {}).get("chat_id"),
                "model": body.get("model"),
                "crisis_flag": crisis,
                "prompt_preview": text[:200],
            }
        )

        if __event_emitter__ and self.valves.show_status:
            try:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"VEIL Tier G · {env.get('minor_profile')} · envelope {env.get('context_id')} · logged for {self.valves.guardian_label}",
                            "done": True,
                        },
                    }
                )
            except Exception:
                pass
        return body

    async def outlet(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __metadata__: Optional[dict] = None,
    ) -> dict:
        try:
            env = self._load_envelope()
        except Exception:
            return body
        if not self._applies(env, __user__):
            return body
        reply = ""
        for m in reversed(body.get("messages", [])):
            if m.get("role") == "assistant":
                reply = str(m.get("content") or "")
                break
        self._log(
            {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "event": "reply",
                "context_id": env.get("context_id"),
                "user_id": (__user__ or {}).get("id"),
                "chat_id": (__metadata__ or {}).get("chat_id"),
                "reply_chars": len(reply),
                "reply_preview": reply[:200],
            }
        )
        return body
