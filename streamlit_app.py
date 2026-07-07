import os
import json
import re
from datetime import datetime, timedelta
from typing import Optional

import streamlit as st
import google.generativeai as genai

# ---------------------------------------------------------------------------
# Background (Photo by Mustafa Erdağ – Pexels #15372566)
# ---------------------------------------------------------------------------
def set_background():
    bg_url = "https://images.pexels.com/photos/15372566/pexels-photo-15372566.jpeg"
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("{bg_url}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        .stApp > header {{ background-color: transparent; }}
        [data-testid="stChatMessageContainer"],
        [data-testid="stVerticalBlock"] {{
            background-color: rgba(0, 0, 0, 0.45);
            border-radius: 10px;
            padding: 8px;
        }}
        h1, h2, h3, p, label, .stMarkdown {{
            color: #ffffff !important;
            text-shadow: 1px 1px 3px rgba(0,0,0,0.8);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

set_background()

# ---------------------------------------------------------------------------
# Menu definition
# ---------------------------------------------------------------------------
MENU = {
    "Ikan Goreng Bumbu Bali": 14_000,
    "Ikan Bakar Sambal Matah": 15_000,
    "Es Teh Manis": 2_000,
}

MENU_TEXT = "\n".join(
    f"  - {name}: Rp {price:,}".replace(",", ".")
    for name, price in MENU.items()
)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
def build_system_prompt() -> str:
    now = datetime.now()
    earliest_reservation = now + timedelta(hours=5)
    return f"""Kamu adalah pelayan ramah di Resto Arsbot. Tugasmu:

1. **Menyambut tamu** dengan hangat dan memperkenalkan menu.
2. **Membantu pelanggan memesan** dari menu berikut:
{MENU_TEXT}

3. **Reservasi meja**: Pelanggan boleh reservasi untuk waktu minimal 5 jam dari sekarang.
   - Waktu sekarang: {now.strftime("%H:%M, %d %B %Y")}
   - Waktu reservasi paling awal: {earliest_reservation.strftime("%H:%M, %d %B %Y")}
   - Jika pelanggan meminta waktu lebih awal dari itu, tolak dengan sopan dan jelaskan aturannya.

4. **Melacak pesanan**: Setiap kali pelanggan memesan item, keluarkan blok JSON tepat setelah teks balasanmu dengan format berikut (WAJIB, jangan dilewati):

```json
{{"action": "add_order", "items": [{{"name": "<nama menu>", "qty": <jumlah>}}]}}
```

   Contoh jika pelanggan pesan 2 Es Teh Manis dan 1 Ikan Goreng Bumbu Bali:
```json
{{"action": "add_order", "items": [{{"name": "Es Teh Manis", "qty": 2}}, {{"name": "Ikan Goreng Bumbu Bali", "qty": 1}}]}}
```

5. **Jika pelanggan meminta nota/invoice/tagihan/bill**, keluarkan blok JSON:
```json
{{"action": "show_invoice"}}
```

6. **Jika pelanggan ingin mengosongkan/membatalkan semua pesanan**, keluarkan:
```json
{{"action": "clear_order"}}
```

Hanya sertakan JSON di akhir balasan, bukan di tengah kalimat. Gunakan bahasa Indonesia yang ramah dan profesional."""

# ---------------------------------------------------------------------------
# Helpers – parse action JSON from assistant reply
# ---------------------------------------------------------------------------
def parse_action(text: str) -> Optional[dict]:
    """Extract the first JSON block from the assistant's response."""
    pattern = r"```json\s*(\{.*?\})\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None


def strip_json_block(text: str) -> str:
    """Remove JSON code blocks from display text."""
    return re.sub(r"```json\s*\{.*?\}\s*```", "", text, flags=re.DOTALL).strip()


def apply_action(action: dict):
    """Update session-state order based on parsed action."""
    if action.get("action") == "add_order":
        for item in action.get("items", []):
            name = item.get("name", "")
            qty = int(item.get("qty", 1))
            # fuzzy match against known menu keys
            matched = next(
                (k for k in MENU if k.lower() == name.lower()), None
            )
            if matched:
                st.session_state.order[matched] = (
                    st.session_state.order.get(matched, 0) + qty
                )
    elif action.get("action") == "clear_order":
        st.session_state.order = {}
    elif action.get("action") == "show_invoice":
        st.session_state.show_invoice = True

# ---------------------------------------------------------------------------
# Invoice renderer
# ---------------------------------------------------------------------------
def render_invoice():
    order = st.session_state.order
    if not order:
        st.info("Belum ada pesanan.")
        return

    now = datetime.now()
    st.markdown("---")
    st.markdown("### 🧾 Invoice Pesanan")
    st.markdown(f"**Tanggal:** {now.strftime('%d %B %Y, %H:%M')}")
    st.markdown("---")

    rows = []
    total = 0
    for name, qty in order.items():
        price = MENU.get(name, 0)
        subtotal = price * qty
        total += subtotal
        rows.append({
            "Menu": name,
            "Qty": qty,
            "Harga Satuan": f"Rp {price:,}".replace(",", "."),
            "Subtotal": f"Rp {subtotal:,}".replace(",", "."),
        })

    st.table(rows)
    st.markdown(f"**Total: Rp {total:,}**".replace(",", "."))
    st.markdown("---")
    st.caption("Terima kasih telah makan di Resto Arsbot! 🙏")

# ---------------------------------------------------------------------------
# API key
# ---------------------------------------------------------------------------
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", os.environ.get("GOOGLE_API_KEY"))
if not GOOGLE_API_KEY:
    st.error(
        "Google API key tidak ditemukan. Tambahkan GOOGLE_API_KEY di .streamlit/secrets.toml.",
        icon="🔑",
    )
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "order" not in st.session_state:
    st.session_state.order = {}
if "show_invoice" not in st.session_state:
    st.session_state.show_invoice = False

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.title("🍽️ Resto Arsbot")
st.write("Selamat datang! Pesan makanan atau reservasi meja dengan mudah.")

# Sidebar – current order summary
with st.sidebar:
    st.header("🛒 Pesanan Saat Ini")
    if st.session_state.order:
        running_total = 0
        for item_name, qty in st.session_state.order.items():
            price = MENU.get(item_name, 0)
            subtotal = price * qty
            running_total += subtotal
            st.write(f"• {item_name} x{qty} — Rp {subtotal:,}".replace(",", "."))
        st.markdown(f"**Total: Rp {running_total:,}**".replace(",", "."))
        if st.button("🗑️ Kosongkan Pesanan"):
            st.session_state.order = {}
            st.session_state.show_invoice = False
            st.rerun()
    else:
        st.write("Belum ada pesanan.")

    st.divider()
    st.caption("Menu hari ini:")
    for m_name, m_price in MENU.items():
        st.caption(f"• {m_name}: Rp {m_price:,}".replace(",", "."))

# ---------------------------------------------------------------------------
# Chat history display
# ---------------------------------------------------------------------------
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Show invoice if triggered
if st.session_state.show_invoice:
    render_invoice()

# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------
if prompt := st.chat_input("Ketik pesanan atau pertanyaan Anda di sini..."):
    # Reset invoice flag on new message
    st.session_state.show_invoice = False

    # Store & display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Build Gemini history (user/model roles) including system prompt as first turn
    system_prompt = build_system_prompt()
    history = [
        {"role": "user", "parts": [system_prompt]},
        {"role": "model", "parts": ["Siap! Saya akan membantu Anda hari ini."]},
    ]
    for m in st.session_state.messages[:-1]:  # exclude latest prompt
        history.append({
            "role": "user" if m["role"] == "user" else "model",
            "parts": [m["content"]],
        })

    chat = model.start_chat(history=history)

    # Stream response
    with st.chat_message("assistant"):
        response_stream = chat.send_message(prompt, stream=True)
        full_response = st.write_stream(
            chunk.text for chunk in response_stream
        )

    # Parse and apply any action embedded in the response
    action = parse_action(full_response)
    if action:
        apply_action(action)

    # Store cleaned response (without raw JSON block) for display history
    display_response = strip_json_block(full_response)
    st.session_state.messages.append({"role": "assistant", "content": display_response})

    # If show_invoice was triggered, render immediately
    if st.session_state.show_invoice:
        render_invoice()

    st.rerun()
