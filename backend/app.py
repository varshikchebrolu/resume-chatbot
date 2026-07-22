from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from google import genai
from google.genai import types
from fastapi.middleware.cors import CORSMiddleware
import rag_pipeline as dp

app = FastAPI(title="Resume Chatbot API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "resume-chatbot"}


def DocumentParsing(query):
    # Step 1: Load and chunk the document (done once)
    chunks = dp.loadAndChunk("data/resume.txt", max_chunk_size=100)
    print(f"Created {len(chunks)} chunks\n")

    # Step 2: Embed the chunks (done once, reuse for multiple queries)
    chunkEmbeddings = dp.embedChunks(chunks)
    print("Chunks embedded\n")

    results = dp.findClosestChunks(query, chunks, chunkEmbeddings, top_n=5, similarity_threshold=0.50)
    prompt = dp.generatePromptWithSimilarities(query,results)
    
    return prompt

async def generate_ai_stream(messages: list):
    api_key = "AIzaSyApRvkcjfhf0wm-r4cuBRG3_VabS0TTs6k"

    client = genai.Client(api_key=api_key)
    
    
    last_msg = messages[-1]
    query_text = ""
    for part in last_msg.get("parts", []):
        if part.get("type") == "text":
            query_text += part.get("text", "")

    final_prompt = DocumentParsing(query_text)
    # Convert UI messages to Gemini format
    contents = []
    contents.append(types.Content(role="model",parts=[types.Part(text=final_prompt)]))
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        # Extract text from parts array
        text = ""
        for part in msg.get("parts", []):
            if part.get("type") == "text":
                text += part.get("text", "")
        if text:
            contents.append(types.Content(role=role, parts=[types.Part(text=text)]))
            
    print(contents)

    response = client.models.generate_content_stream(
        model="gemini-2.5-flash", contents=contents
    )

    # TextStreamChatTransport expects plain text chunks
    for chunk in response:
        if chunk.text:
            yield chunk.text


@app.post("/getAIResponse")
async def main(request: Request):
    body = await request.json()
    messages = body.get("messages", [])

    return StreamingResponse(
        generate_ai_stream(messages),
        media_type="text/plain; charset=utf-8",
    )
