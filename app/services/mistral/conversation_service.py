import json

from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import JSONResponse
from app.core.config import settings
from mistralai import Mistral, SDKError

from app.models.agent import Agent
from app.models.topic import Topic
from app.models.topic_chat import TopicChat
from app.utils.random_generator import generate_random_string


class MistralConversationService:
    def request_ai(self, prompt: str):
        # model = "ai-small-2506"
        model = "mistral-large-2512"

        client = Mistral(api_key=settings.MISTRAL_API_KEY)

        chat_response = client.chat.complete(
            model=model,
            messages=[
                {"role": "user", "content": f"{prompt}"}
            ]
        )

        # print("Res: "+chat_response)
        return chat_response.choices[0].message.content

    def create_agent(self, model):
        api_key = settings.MISTRAL_API_KEY
        client = Mistral(api_key)

        description_creator_agent = client.beta.agents.create(
            model=model,
            description="A simple Agent to make summaries of chat.",
            name="Chat Summarizer Agent",
            instructions="You are a chat summarizer agent. Your task is to take the 1st user message, then ask questions to clarify the users need and based"
                         " on conversation generate a summary of the "
                         "discussion so far. "
                         "Instructions to be strictly obey: "
                         "1. When asking questions, return only a json like {'question':"
                         " 'your question here'} and when providing the final summary, return only a json like {'summary': 'your summary here'}. "
                         "Return ONLY valid JSON. No prose. No markdown."
                         "2. The user will most probably ask for update on some topic, so make sure to ask relevant questions to get more context of "
                         "users topic. "
                         "3. Dont ask questions about the method user would want to get this update"
                         "4. When providing the final summary, make sure it is concise and captures all key points discussed in the chat."
                         "5. Ask at least 3 questions before providing the final summary. You can go even more if seem necessary."
                         "6. Questions are only to asked to get more context about the topic user wants the summary on. Nothing else",

            completion_args={
                "temperature": 1.2,
                "top_p": 0.98,
            }
        )

        return description_creator_agent

        return description_creator_agent

    def start_conversation(self, agent_id:str,  message: str):
        api_key = settings.MISTRAL_API_KEY
        client = Mistral(api_key)
        response = client.beta.conversations.start(
            agent_id=agent_id,
            inputs=message,
            # inputs=[{"role": "user", "content": "Who is Albert Einstein?"}] is also valid
            # store=False
        )

        return response

    def continue_conversation(self, conversation_id: str, message: str):
        api_key = settings.MISTRAL_API_KEY
        client = Mistral(api_key)

        response = client.beta.conversations.append(
            conversation_id=conversation_id,
            inputs=message,
            completion_args={
                "temperature": 0.3,
                "top_p": 0.95,
            }
        )
        return response

    def chat_with_ai(self, message:str, topic_id:str, current_user:dict, db:Session):

        global first_response, agent
        try:

            topic = db.query(Topic).filter(Topic.id == topic_id, Topic.associated_user_id == current_user["user_id"]).first()

            if not topic:
                raise Exception("Topic not found")

            # user message store
            topic_chat_user = TopicChat(
                id = generate_random_string(32),
                associated_topic_id=topic_id,
                chat_message=message,
                sent_by_user=True
            )
            db.add(topic_chat_user)


            # check if first chat
            conversation_id= topic.ai_conversation_id
            ai_message = ""
            if not conversation_id:
                # First message in the conversation
                try:
                    agent= db.query(Agent).filter(Agent.model == topic.model).first()
                    if not agent:
                        agent_result = self.create_agent(topic.model)
                        agent = Agent(
                            id=generate_random_string(32),
                            model=topic.model,
                            agent_id=agent_result.id
                        )
                        db.add(agent)

                    first_response = self.start_conversation(agent.agent_id, message)

                except SDKError as e:
                    # Check HTTP status code only
                    if e.status_code==404:
                        agent_result = self.create_agent(topic.model)
                        agent_id = agent_result.id
                        agent.agent_id = agent_result.id
                        first_response = self.start_conversation(agent.agent_id, message)
                    else:
                        # Any other SDK error
                        raise e
                print(first_response)
                if not first_response:
                    raise Exception("Failed to get response from AI")

                conversation_id = first_response.conversation_id

                if not conversation_id:
                    raise Exception("Failed to get conversation ID from AI")

                first_message = first_response.outputs[0].content

                if not first_message:
                    raise Exception("Failed to get message from AI")

                topic.ai_conversation_id = conversation_id
                db.add(topic)
                ai_message = first_message

            else:

                response = self.continue_conversation(conversation_id, message)
                print(response)

                if not response:
                    raise Exception("Failed to get response from AI")

                ai_message = response.outputs[0].content

                if not ai_message:
                    raise Exception("Failed to get message from AI")

            try:
                clean_message = ai_message.replace("```json", "").replace("```", "").strip()
                ai_message_json = json.loads(clean_message)
            except json.JSONDecodeError:
                raise Exception("AI did not return valid JSON")

            if not ai_message_json:
                raise Exception("Failed to parse AI message")

            if "question" in ai_message_json :
                ai_message = ai_message_json["question"]

            elif "summary" in ai_message_json:
                ai_message = ai_message_json["summary"]

                topic.description = ai_message_json["summary"]
                db.add(topic)

            else:
                raise Exception("AI response missing required fields")

            topic_chat = TopicChat(
                id = generate_random_string(32),
                associated_topic_id=topic_id,
                chat_message=ai_message,
                sent_by_user=False
            )
            db.add(topic_chat)

            db.commit()
            db.refresh(topic_chat)
            db.refresh(topic)

            if "question" in ai_message_json:
                return JSONResponse(content={"ai_message": ai_message},
                                    status_code=status.HTTP_200_OK)

            elif "summary" in ai_message_json:
                return JSONResponse(content={"ai_message": ai_message, "topic_description": topic.description},
                                    status_code=status.HTTP_200_OK)
            elif None:
                return JSONResponse(content={"message": "AI response missing required fields"},
                                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            db.rollback()
            print(e)
            return JSONResponse(content={"message": e}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)



    # def generate_new_agent_id(self, db:Session, model):
    #     agent = db.query(Agent).filter(Agent.model == model).first()
    #     if not agent:
    #         raise Exception("Agent not found")
    #


