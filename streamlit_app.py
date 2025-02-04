import streamlit as st
import openai
import fitz  # PyMuPDF per estrarre testo dal PDF
import os
import tempfile

# Configura l'API Key di OpenAI
openai.api_key = st.secrets["openai_api_key"]

# Configura lo stato della sessione
if "chats" not in st.session_state:
    st.session_state.chats = []  # Lista per memorizzare le chat
if "selected_chat" not in st.session_state:
    st.session_state.selected_chat = None  # Chat selezionata
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""  # Testo estratto dal PDF
if "tone_of_voice" not in st.session_state:
    st.session_state.tone_of_voice = "Rispondi in modo sintetico, chiaro e professionale."  # Prompt predefinito
if "show_tone_settings" not in st.session_state:
    st.session_state.show_tone_settings = False  # Controllo per mostrare il box di impostazione del tone of voice
if "language" not in st.session_state:
    st.session_state.language = "it"  # Imposta la lingua predefinita in italiano

# Mostra il logo dell'app
st.image("media/mida_logo_1000.png", width=350)

# Funzione per estrarre testo dal PDF
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = "\n".join([page.get_text() for page in doc])
    return text

# Funzione per caricare un PDF
uploaded_file = st.sidebar.file_uploader("📄 Carica il documento PDF da memorizzare", type=["pdf"])
if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(uploaded_file.read())
        temp_pdf_path = temp_file.name

    # Estrarre testo dal PDF e salvarlo nella sessione
    st.session_state.pdf_text = extract_text_from_pdf(temp_pdf_path)
    st.sidebar.success("PDF caricato e analizzato con successo!")

# Funzione per troncare il contesto se diventa troppo lungo
def truncate_messages(messages, max_tokens=30000):
    total_tokens = 0
    truncated_messages = []
    for message in reversed(messages):  # Inizia dagli ultimi messaggi
        message_tokens = len(message["content"].split())  # Stima dei token
        if total_tokens + message_tokens > max_tokens:
            break
        truncated_messages.insert(0, message)  # Aggiunge il messaggio mantenendo l'ordine
        total_tokens += message_tokens
    return truncated_messages

# Funzione per inviare una domanda a GPT-4-turbo con il PDF mantenendo il contesto
def ask_gpt_with_pdf(query):
    if not st.session_state.pdf_text:
        return "⚠️ Carica prima il tuo documento PDF nelle impostazioni."
    
    chat_data = next(c for c in st.session_state.chats if c["id"] == st.session_state.selected_chat)

    # Creiamo la lista dei messaggi includendo lo storico della conversazione e tronchiamo se troppo lunga
    messages = [{"role": "system", "content": f"{st.session_state.tone_of_voice}\nRispondi solo basandoti sul documento caricato."}]
    truncated_chat = truncate_messages(chat_data["messages"], 4000)
    messages.extend(truncated_chat)  # Aggiunge lo storico ridotto
    messages.append({"role": "user", "content": f"Documento:\n{st.session_state.pdf_text}\n\nDomanda: {query}"})  # Aggiunge il documento e la nuova domanda

    response = openai.chat.completions.create(
        model="gpt-4-turbo",
        messages=messages
    )
    
    return response.choices[0].message.content

# Layout della sidebar per la gestione delle chat
st.sidebar.title("Gestione conversazioni")
if st.sidebar.button("➕ Nuova Conversazione"):
    chat_id = f"Conversazione {len(st.session_state.chats) + 1}"
    st.session_state.chats.append({"id": chat_id, "messages": []})
    st.session_state.selected_chat = chat_id

# Visualizza le chat esistenti nella sidebar
for chat in st.session_state.chats:
    if st.sidebar.button(chat["id"]):
        st.session_state.selected_chat = chat["id"]

# Pulsante per mostrare/nascondere le impostazioni del tone of voice
if st.sidebar.button("⚙️ Imposta Tone of Voice"):
    st.session_state.show_tone_settings = not st.session_state.show_tone_settings

if st.session_state.show_tone_settings:
    st.sidebar.text_area("Modifica il tone of voice:", value=st.session_state.tone_of_voice, key="tone_of_voice")

# Area principale della chat
st.title("🤖 Chiedi a MIDA")
if not st.session_state.selected_chat:
    st.write("Seleziona una conversazione o creane una nuova dalla barra laterale.")
else:
    chat_data = next(c for c in st.session_state.chats if c["id"] == st.session_state.selected_chat)
    
    # Visualizza la conversazione
    for message in chat_data["messages"]:
        role = "👤" if message["role"] == "user" else "🤖"
        st.write(f"{role}: {message['content']}")
    
    # Box di input per l'utente
    user_input = st.text_input("Fai una domanda sul tuo PDF:")
    if st.button("Invia") and user_input:
        response = ask_gpt_with_pdf(user_input)
        chat_data["messages"].append({"role": "user", "content": user_input})
        chat_data["messages"].append({"role": "assistant", "content": response})
        #st.session_state["user_input"] = ""  # Resetta il textbox dopo l'invio
        st.rerun()
