import os
import streamlit as st
import google.generativeai as genai

# Show title and description.
st.title("💬 Chatbot")
st.write("This is a simple chatbot that uses Google's Gemini model to generate responses.")

# Load API key automatically from Streamlit secrets or environment variable.
# No manual input required.
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", os.environ.get("GOOGLE_API_KEY"))

if not GOOGLE_API_KEY:
    st.error("Google API key not found. Please set GOOGLE_API_KEY in .streamlit/secrets.toml or as an environment variable.", icon="�")
    st.stop()

# Configure the Gemini client with the API key.
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# Create a session state variable to store the chat messages. This ensures that the
# messages persist across reruns.
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display the existing chat messages via `st.chat_message`.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Create a chat input field to allow the user to enter a message. This will display
# automatically at the bottom of the page.
if prompt := st.chat_input("What is up?"):

    # Store and display the current prompt.
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Build conversation history in Gemini format.
    history = [
        {
            "role": "user" if m["role"] == "user" else "model",
            "parts": [m["content"]],
        }
        for m in st.session_state.messages[:-1]  # exclude the latest prompt
    ]

    # Start a chat session with history and send the latest message.
    chat = model.start_chat(history=history)

    # Stream the response to the chat using `st.write_stream`, then store it in
    # session state.
    with st.chat_message("assistant"):
        response_stream = chat.send_message(prompt, stream=True)
        response = st.write_stream(
            (chunk.text for chunk in response_stream)
        )

    st.session_state.messages.append({"role": "assistant", "content": response})
