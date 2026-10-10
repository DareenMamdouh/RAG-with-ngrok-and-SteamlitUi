import requests
import streamlit as st

st.set_page_config(page_title="PDF Q&A with Mistral", page_icon="📄", layout="centered")

# ---------------- Sidebar: connection + PDF ----------------
st.sidebar.header("1. Backend settings")
backend_url = st.sidebar.text_input("ngrok URL", placeholder="https://xxxx.ngrok-free.app")
api_key = st.sidebar.text_input("API key", value="secret123", type="password")
st.sidebar.caption("Run the Kaggle notebook first, then paste the public URL it prints.")

headers = {
    "Authorization": f"Bearer {api_key}",
    "ngrok-skip-browser-warning": "true",
}
base = backend_url.rstrip("/")

st.sidebar.header("2. Upload your PDF")
pdf = st.sidebar.file_uploader("Choose a PDF", type=["pdf"])

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pdf_name" not in st.session_state:
    st.session_state.pdf_name = None

if st.sidebar.button("Process PDF", type="primary"):
    if not base:
        st.sidebar.error("Add the ngrok URL first.")
    elif pdf is None:
        st.sidebar.error("Choose a PDF first.")
    else:
        try:
            with st.spinner("Reading and indexing the PDF..."):
                res = requests.post(
                    f"{base}/upload",
                    headers=headers,
                    files={"file": (pdf.name, pdf.getvalue(), "application/pdf")},
                    timeout=300,
                )
            if res.status_code == 200:
                info = res.json()
                st.session_state.pdf_name = info["filename"]
                st.session_state.messages = []
                st.sidebar.success(f"Ready: {info['filename']} ({info['pages']} pages, {info['chunks']} chunks)")
            else:
                st.sidebar.error(f"Error {res.status_code}: {res.text[:300]}")
        except Exception as e:
            st.sidebar.error(f"Could not reach the backend: {e}")

if st.sidebar.button("Clear chat"):
    st.session_state.messages = []

# ---------------- Main: chat ----------------
st.title("📄 PDF Q&A with Mistral")
st.caption("RAG: your question is matched with the most relevant parts of the PDF, then Mistral answers from them.")

if st.session_state.pdf_name:
    st.success(f"Current PDF: {st.session_state.pdf_name}")
else:
    st.info("Add the backend URL, upload a PDF, and click **Process PDF** in the sidebar to start.")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("sources"):
            with st.expander("Sources from the PDF"):
                for s in m["sources"]:
                    st.markdown(f"**Page {s['page']}**")
                    st.caption(s["text"])

question = st.chat_input(
    "Ask a question about the PDF",
    disabled=st.session_state.pdf_name is None,
)

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Thinking..."):
                res = requests.post(
                    f"{base}/ask", headers=headers, json={"question": question}, timeout=300
                )
            if res.status_code == 200:
                data = res.json()
                st.markdown(data["answer"])
                with st.expander("Sources from the PDF"):
                    for s in data["sources"]:
                        st.markdown(f"**Page {s['page']}**")
                        st.caption(s["text"])
                st.session_state.messages.append(
                    {"role": "assistant", "content": data["answer"], "sources": data["sources"]}
                )
            else:
                st.error(f"Error {res.status_code}: {res.text[:300]}")
        except Exception as e:
            st.error(f"Could not reach the backend: {e}")
