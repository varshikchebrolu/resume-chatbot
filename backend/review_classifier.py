from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError, Field
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider


class customerReviewData(BaseModel):
    id: int = Field(
        description="Id for the customer review dat, can be a random 16 digit string"
    )
    customerReview: str = Field(description="review given by the customer")
    reviewTag: str = Field(
        description="the tag for the review which will help the business to route it accordingly"
    )


provider = GoogleProvider(api_key="AIzaSyApRvkcjfhf0wm-r4cuBRG3_VabS0TTs6k")
model = GoogleModel('gemini-3.5-flash', provider=provider)
agent = Agent(
    model,
    output_type=list[customerReviewData],
    instructions="you are an expert reviewer and backend data parser. Carefully extract the data required from the agent output",
)


def checkCustomerReviews():
    customerReviews = [
        "the fedback button is not working properly",
        "I like the app",
        "the marketing email offer I got is not applying to the ",
    ]

    initAIcall(
        f"take in the customer reviews, {customerReviews} and assign a tag to them a tag like bug, feature or review. Give me a structured output for each input."
    )


def initAIcall(content: str):
    api_key = "AIzaSyApRvkcjfhf0wm-r4cuBRG3_VabS0TTs6k"

    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig()

    response = client.models.generate_content(
        model="gemini-3.5-flash", contents=content
    )

    text_response = response.candidates[0].content.parts[0].text
    print(text_response)
    result = agent.run_sync(text_response)

    print(result.output)


def app():
    checkCustomerReviews()


if __name__ == "__main__":
    app()
