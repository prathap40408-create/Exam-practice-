
import json
import re
import streamlit as st
from pypdf import PdfReader
from openai import OpenAI

st.set_page_config(page_title="Exam Study Hub", page_icon="📚", layout="wide")
st.title("📚 Exam Study Hub")

# ---------- API and PDF helpers ----------

def get_client():
    key = st.secrets.get("OPENAI_API_KEY", "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")
    if not key:
        st.error("Add OPENAI_API_KEY in Streamlit Cloud → Settings → Secrets.")
        st.stop()
    return OpenAI(api_key=key)


def extract_pdf(upload):
    reader = PdfReader(upload)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    if len(text.strip()) < 100:
        raise ValueError(
            "Very little text found. This may be a scanned PDF. "
            "Use a searchable PDF or OCR it first."
        )
    return text


def clean(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def norm(text):
    return clean(text).casefold()


def make_chunks(text, size=8000, overlap=400):
    text = clean(text)
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def ask_json(client, model, instructions, prompt, tokens=6000):
    response = client.responses.create(
        model=model,
        instructions=instructions,
        input=prompt,
        text={"format": {"type": "json_object"}},
        max_output_tokens=tokens,
    )
    result = json.loads(response.output_text)
    if not isinstance(result, dict):
        raise ValueError("Unexpected response format.")
    return result


def source_supports(quote, source):
    quote = norm(quote)
    source = norm(source)
    return len(quote) >= 15 and quote in source


# ---------- MCQ generator ----------

def generate_mcqs(text, target, exam, model, client, progress, status):
    chunks = make_chunks(text)
    results = []
    seen = set()

    # Limit API calls to help control usage.
    max_rounds = min(30, max(8, target * 2))

    for round_no in range(max_rounds):
        if len(results) >= target:
            break

        source = chunks[round_no % len(chunks)]
        count = min(6, target - len(results))
        previous = "\n".join(
            q["question"] for q in results[-60:]
        ) or "(none)"

        prompt = f"""
Create up to {count} new multiple-choice questions for {exam}.
Use ONLY the source passage below.

Return this JSON structure:
{{
  "questions": [
    {{
      "question": "Question text",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": "Exact text of the correct option",
      "explanation": "Why this answer is correct",
      "source_quote": "Exact quotation copied from the source"
    }}
  ]
}}

STRICT RULES:
- Test important facts and concepts stated in the passage.
- Exactly four distinct options and exactly one correct answer.
- Distractors must be plausible, relevant to the same subject, and similar in length.
- Avoid silly options, obvious clues, and "all/none of the above".
- Do not make the correct option consistently longer than the others.
- The answer must match one option exactly.
- Explain the answer using the passage.
- The source_quote must be an exact passage substring supporting the answer.
- Do not invent facts, dates, names, or statistics.
- Do not repeat these questions:
{previous}

SOURCE:
{source}
"""

        try:
            data = ask_json(
                client,
                model,
                "You are a careful competitive-exam question setter. Follow all source-only rules.",
                prompt,
            )

            candidates = data.get("questions", [])
            if not isinstance(candidates, list):
                continue

            # Independent review: reject weak or unsupported questions.
            review_input = json.dumps(
                {"source": source, "questions": candidates},
                ensure_ascii=False,
            )

            review = ask_json(
                client,
                model,
                """Review the proposed MCQs against the source.
Return JSON:
{"reviews":[{"question":"exact original question","valid":true}]}

Set valid=true only if the source supports the correct answer,
the answer is unambiguous, and all four options are plausible,
distinct, and relevant. If unsure, use false. Do not rewrite questions.""",
                review_input,
                tokens=4000,
            )

            approved = {
                norm(item.get("question", "")): item.get("valid") is True
                for item in review.get("reviews", [])
                if isinstance(item, dict)
            }

            for item in candidates:
                if not isinstance(item, dict):
                    continue

                question = clean(item.get("question", ""))
                options = item.get("options", [])
                answer = clean(item.get("answer", ""))
                explanation = clean(item.get("explanation", ""))
                quote = clean(item.get("source_quote", ""))

                if not question or norm(question) in seen:
                    continue
                if approved.get(norm(question)) is not True:
                    continue
                if not isinstance(options, list) or len(options) != 4:
                    continue

                options = [clean(option) for option in options]
                if any(not option for option in options):
                    continue
                if len(set(map(norm, options))) != 4:
                    continue
                if options.count(answer) != 1:
                    continue
                if not source_supports(quote, source):
                    continue
                if not explanation:
                    continue

                results.append({
                    "question": question,
                    "options": options,
                    "answer": answer,
                    "correct_index": options.index(answer),
                    "explanation": explanation,
                    "source_quote": quote,
                })
                seen.add(norm(question))

                if len(results) >= target:
                    break

        except Exception as exc:
            status.warning(f"A generation batch failed: {exc}")

        progress.progress(min(1.0, len(results) / target))
        status.info(f"Reviewed MCQs: {len(results)} / {target}")

    status.empty()
    progress.progress(1.0)
    return results[:target]


# ---------- Independent flashcard generator ----------

def generate_flashcards(text, target, exam, model, client, progress, status):
    chunks = make_chunks(text)
    results = []
    seen = set()
    max_rounds = min(30, max(8, target * 2))

    for round_no in range(max_rounds):
        if len(results) >= target:
            break

        source = chunks[round_no % len(chunks)]
        count = min(10, target - len(results))
        previous = "\n".join(card["front"] for card in results[-80:]) or "(none)"

        prompt = f"""
Create up to {count} useful revision flashcards for {exam}.
Use ONLY the source passage below.

Return JSON:
{{
  "flashcards": [
    {{
      "front": "A specific question or recall prompt",
      "back": "Direct, accurate answer",
      "explanation": "Short explanation for revision",
      "source_quote": "Exact quotation copied from the passage"
    }}
  ]
}}

RULES:
- These must be independent flashcards, NOT multiple-choice questions.
- One useful fact or closely related concept per card.
- The front must ask a specific question, not "Explain this topic".
- The back must answer the front directly.
- Include necessary dates, names, and qualifiers.
- Avoid repeated or nearly identical cards.
- Use only facts supported by the source. Do not invent information.
- source_quote must be an exact substring from the source.
- Do not repeat these card fronts:
{previous}

SOURCE:
{source}
"""

        try:
            data = ask_json(
                client,
                model,
                "You create accurate source-based flashcards for competitive exams.",
                prompt,
                tokens=5000,
            )

            for item in data.get("flashcards", []):
                if not isinstance(item, dict):
                    continue

                front = clean(item.get("front", ""))
                back = clean(item.get("back", ""))
                explanation = clean(item.get("explanation", ""))
                quote = clean(item.get("source_quote", ""))

                if not front or not back or not explanation:
                    continue
                if norm(front) in seen:
                    continue
                if len(front) > 300 or len(back) > 600:
                    continue
                if not source_supports(quote, source):
                    continue

                results.append({
                    "front": front,
                    "back": back,
                    "explanation": explanation,
                    "source_quote": quote,
                })
                seen.add(norm(front))

                if len(results) >= target:
                    break

        except Exception as exc:
            status.warning(f"A flashcard batch failed: {exc}")

        progress.progress(min(1.0, len(results) / target))
        status.info(f"Flashcards: {len(results)} / {target}")

    status.empty()
    progress.progress(1.0)
    return results[:target]


def download_json(label, data, filename, key):
    st.download_button(
        label,
        data=json.dumps(data, ensure_ascii=False, indent=2),
        file_name=filename,
        mime="application/json",
        key=key,
    )


# ---------- Session state ----------

if "questions" not in st.session_state:
    st.session_state.questions = []
if "flashcards" not in st.session_state:
    st.session_state.flashcards = []
if "test_answers" not in st.session_state:
    st.session_state.test_answers = {}
if "test_submitted" not in st.session_state:
    st.session_state.test_submitted = False
if "flash_index" not in st.session_state:
    st.session_state.flash_index = 0


# ---------- Sidebar ----------

with st.sidebar:
    st.header("Exam settings")
    exam = st.selectbox(
        "Target exam",
        ["SSC CPO", "SSC CGL", "RRB NTPC", "IB ACIO", "CAPF AC",
         "General competitive exams"],
    )
    model = st.selectbox(
        "AI model",
        ["gpt-4o-mini", "gpt-4o"],
        index=0,
    )
    st.caption("The larger model may cost more per request.")

page = st.radio(
    "Section",
    ["Home", "PDF to MCQ", "Mock Test", "Flashcards"],
    horizontal=True,
)


# ---------- Home ----------

if page == "Home":
    st.subheader("Your study workspace")

    col1, col2 = st.columns(2)
    col1.metric("Saved MCQs", len(st.session_state.questions))
    col2.metric("Saved flashcards", len(st.session_state.flashcards))

    st.markdown("""
    **PDF to MCQ:** Upload a PDF to create questions and explanations.

    **Mock Test:** Attempt generated MCQs and calculate your score.

    **Flashcards:** Upload a separate PDF to create question-and-answer cards.
    """)

    st.warning(
        "The app checks supporting quotations and reviews generated questions, "
        "but AI can still make mistakes. Verify important exam facts against the PDF."
    )


# ---------- PDF to MCQ ----------

elif page == "PDF to MCQ":
    st.subheader("Generate MCQs from a PDF")
    st.write("This upload is used only for the MCQ generator.")

    uploaded = st.file_uploader(
        "Upload PDF for MCQs",
        type=["pdf"],
        key="mcq_upload",
    )
    target = st.number_input(
        "Number of MCQs",
        min_value=5,
        max_value=500,
        value=20,
        step=5,
        key="mcq_count",
    )

    if st.button("Generate MCQs", type="primary"):
        if uploaded is None:
            st.error("Upload a PDF first.")
        else:
            try:
                text = extract_pdf(uploaded)
                client = get_client()
                progress = st.progress(0)
                status = st.empty()

                with st.spinner("Generating and reviewing MCQs. API usage may incur charges."):
                    questions = generate_mcqs(
                        text, int(target), exam, model,
                        client, progress, status
                    )

                st.session_state.questions = questions
                st.session_state.test_answers = {}
                st.session_state.test_submitted = False

                if questions:
                    st.success(f"Generated {len(questions)} MCQs.")
                else:
                    st.warning(
                        "No questions passed the checks. Try a smaller count "
                        "or a text-based PDF."
                    )

            except Exception as exc:
                st.error(f"Could not generate MCQs: {exc}")

    if st.session_state.questions:
        questions = st.session_state.questions
        st.divider()
        st.write(f"**Available MCQs: {len(questions)}**")

        download_json(
            "Download MCQs as JSON",
            {"exam": exam, "questions": questions},
            "mcq_questions.json",
            "download_mcqs",
        )

        with st.expander("Preview questions"):
            for i, q in enumerate(questions, 1):
                st.markdown(f"**{i}. {q['question']}**")
                for option in q["options"]:
                    st.write(f"- {option}")
                st.write(f"**Answer:** {q['answer']}")
                st.write(f"**Explanation:** {q['explanation']}")
                st.caption(f"Source: {q['source_quote']}")
                st.divider()


# ---------- Mock Test ----------

elif page == "Mock Test":
    st.subheader("Mock Test")
    questions = st.session_state.questions

    if not questions:
        st.info("Generate MCQs in the PDF to MCQ section first.")
    else:
        st.write(f"Questions: **{len(questions)}**")

        if st.button("Reset test"):
            st.session_state.test_answers = {}
            st.session_state.test_submitted = False
            st.rerun()

        with st.form("mock_test"):
            submitted_answers = {}

            for i, q in enumerate(questions, 1):
                st.markdown(f"**Q{i}. {q['question']}**")
                choices = ["— Unanswered —"] + q["options"]

                selected = st.radio(
                    f"Answer Q{i}",
                    choices,
                    index=0,
                    key=f"answer_{i}",
                    label_visibility="collapsed",
                )
                submitted_answers[str(i)] = selected
                st.divider()

            submitted = st.form_submit_button("Submit test", type="primary")

        if submitted:
            st.session_state.test_answers = submitted_answers
            st.session_state.test_submitted = True

        if st.session_state.test_submitted:
            correct = wrong = unanswered = 0

            for i, q in enumerate(questions, 1):
                chosen = st.session_state.test_answers.get(
                    str(i), "— Unanswered —"
                )

                if chosen == "— Unanswered —":
                    unanswered += 1
                elif chosen == q["answer"]:
                    correct += 1
                else:
                    wrong += 1

            score = correct - (wrong * 0.33)

            st.subheader("Your result")
            a, b, c, d = st.columns(4)
            a.metric("Score", f"{score:.2f} / {len(questions)}")
            b.metric("Correct", correct)
            c.metric("Incorrect", wrong)
            d.metric("Unanswered", unanswered)

            st.caption("Scoring: +1 correct, −0.33 incorrect, 0 unanswered.")

            st.subheader("Answer explanations")
            for i, q in enumerate(questions, 1):
                chosen = st.session_state.test_answers.get(
                    str(i), "— Unanswered —"
                )
                if chosen == q["answer"]:
                    result = "Correct"
                elif chosen == "— Unanswered —":
                    result = "Unanswered"
                else:
                    result = "Incorrect"

                with st.expander(f"Q{i} — {result}: {q['question']}"):
                    st.write(f"Your answer: {chosen}")
                    st.write(f"Correct answer: {q['answer']}")
                    st.write(f"Explanation: {q['explanation']}")
                    st.caption(f"Source: {q['source_quote']}")


# ---------- Separate Flashcards PDF upload ----------

elif page == "Flashcards":
    st.subheader("Create flashcards from a separate PDF")
    st.write(
        "Upload any PDF here. It does not need to be the same document "
        "you uploaded for MCQs."
    )

    uploaded = st.file_uploader(
        "Upload PDF for flashcards",
        type=["pdf"],
        key="flashcards_upload",
    )
    target = st.number_input(
        "Number of flashcards",
        min_value=5,
        max_value=500,
        value=30,
        step=5,
        key="flashcard_count",
    )

    if st.button("Generate flashcards", type="primary"):
        if uploaded is None:
            st.error("Upload a PDF first.")
        else:
            try:
                text = extract_pdf(uploaded)
                client = get_client()
                progress = st.progress(0)
                status = st.empty()

                with st.spinner("Creating independent revision flashcards. API usage may incur charges."):
                    cards = generate_flashcards(
                        text, int(target), exam, model,
                        client, progress, status
                    )

                st.session_state.flashcards = cards
                st.session_state.flash_index = 0

                if cards:
                    st.success(f"Created {len(cards)} flashcards.")
                else:
                    st.warning(
                        "No cards passed the source checks. Try a smaller count "
                        "or a text-based PDF."
                    )

            except Exception as exc:
                st.error(f"Could not generate flashcards: {exc}")

    cards = st.session_state.flashcards

    if cards:
        st.divider()
        st.write(f"**Available flashcards: {len(cards)}**")

        download_json(
            "Download flashcards as JSON",
            {"exam": exam, "flashcards": cards},
            "flashcards.json",
            "download_flashcards",
        )

        index = min(st.session_state.flash_index, len(cards) - 1)
        card = cards[index]

        st.markdown(f"### Card {index + 1} of {len(cards)}")

        with st.container(border=True):
            st.markdown("**FRONT — Question**")
            st.write(card["front"])

            if st.toggle("Reveal answer", key=f"reveal_{index}"):
                st.markdown("**BACK — Answer**")
                st.write(card["back"])
                st.markdown("**Explanation**")
                st.write(card["explanation"])
                st.caption(f"Source: {card['source_quote']}")

        left, middle, right = st.columns([1, 2, 1])

        with left:
            if st.button("← Previous", disabled=index == 0):
                st.session_state.flash_index = index - 1
                st.rerun()

        with middle:
            chosen_card = st.selectbox(
                "Go to card",
                list(range(1, len(cards) + 1)),
                index=index,
                key="card_selector",
            )
            if chosen_card - 1 != index:
                st.session_state.flash_index = chosen_card - 1
                st.rerun()

        with right:
            if st.b
