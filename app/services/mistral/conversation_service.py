import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import JSONResponse
from app.core.config import settings
from mistralai import Mistral, SDKError

from app.db.session import SessionLocal
from app.models.agent import Agent
from app.models.topic import Topic
from app.models.topic_chat import TopicChat
from app.models.update import Update
from app.models.user import User
from app.utils.random_generator import generate_random_string
from app.services.email_service import send_updates_email
from app.services.serpapi.search_serp import search_serp_with_topic_description
from app.services.task_schedule.schedule_update_collection_service import (
    scheduler,
    get_session_for_job,
)


class MistralConversationService:
    def request_ai(self, prompt: str):
        model = "mistral-large-2512"

        client = Mistral(api_key=settings.MISTRAL_API_KEY)

        chat_response = client.chat.complete(
            model=model,
            messages=[
                {"role": "user", "content": f"{prompt}"}
            ]
        )

        return chat_response.choices[0].message.content

    def request_ai_with_chunking(self, base_prompt: str, data: str, max_chars: int = 15000):
  
        if len(data) <= max_chars:
            full_prompt = base_prompt.replace("{DATA}", data)
            return self.request_ai(full_prompt)
        
        chunks = []
        current_chunk = ""
        
        try:
            data_obj = json.loads(data)
            if isinstance(data_obj, list):
                chunk_size = max(1, len(data_obj) // ((len(data) // max_chars) + 1))
                for i in range(0, len(data_obj), chunk_size):
                    chunk_data = data_obj[i:i + chunk_size]
                    chunks.append(json.dumps(chunk_data, ensure_ascii=False))
            else:
                chunks = [data[i:i + max_chars] for i in range(0, len(data), max_chars)]
        except json.JSONDecodeError:
            chunks = [data[i:i + max_chars] for i in range(0, len(data), max_chars)]
        
        results = []
        for i, chunk in enumerate(chunks):
            chunk_prompt = base_prompt.replace("{DATA}", chunk)
            if len(chunks) > 1:
                chunk_prompt += f"\n(Processing chunk {i+1} of {len(chunks)})"
            
            result = self.request_ai(chunk_prompt)
            results.append(result)
        
        return self._merge_chunked_results(results)
    
    def _merge_chunked_results(self, results: list) -> str:
   
        if len(results) == 1:
            return results[0]
        
        merged_list = []
        all_lists = True
        
        for result in results:
            try:
                clean_result = result.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(clean_result)
                if isinstance(parsed, list):
                    merged_list.extend(parsed)
                else:
                    all_lists = False
                    break
            except:
                all_lists = False
                break
        
        if all_lists and merged_list:
            return json.dumps(merged_list, ensure_ascii=False)
        
        return "\n".join(results)

    def create_agent(self, model):
        api_key = settings.MISTRAL_API_KEY
        client = Mistral(api_key)

        description_creator_agent = client.beta.agents.create(
            model=model,
            description="A simple Agent to make summaries of chat.",
            name="Chat Summarizer Agent",
            instructions="You are a chat summarizer agent. Your task is to take the 1st user message, then ask questions to clarify the users need and based"\
                         " on conversation generate a summary of the "\
                         "discussion so far. "\
                         "Instructions to be strictly followed: "\
                         "1. CRITICAL: Ask ONLY ONE question per response. Never ask multiple questions at once. "\
                         "2. When asking a question, return ONLY a single JSON object like {'question': 'your question here'}. "\
                         "When providing the final summary, return ONLY a single JSON object like {'summary': 'your summary here'}. "\
                         "Return ONLY valid JSON. No prose. No markdown. No multiple JSON objects."\
                         "3. The user will ask for updates on some topic. Ask relevant questions ONE AT A TIME to get more context about the user's topic. "\
                         "4. Do NOT ask questions about the method or delivery format the user would want to receive updates."\
                         "5. Build the conversation naturally by asking follow-up questions based on the user's previous responses. "\
                         "6. Ask at least 3-5 questions total before providing the final summary. Take your time to gather comprehensive information."\
                         "7. Questions should ONLY gather more context about the topic user wants updates on. Nothing else."\
                         "8. Once you have enough information (after at least 3-5 exchanges), provide a concise summary that captures all key points discussed. The summary  should only include the topics description, dont start like The user want update on or some other starting, give the summary directly"\
                         "9. REMEMBER: ONE question at a time. Never generate multiple question objects in a single response.",

            completion_args={
                "temperature": 0.8,
                "top_p": 0.98,
            }
        )

        return description_creator_agent

        return description_creator_agent

    def run_serp_topic_enrichment(self, topic: Topic, db: Session):

        result = {
            "status": "not_started",
            "updates_created": [],
            "errors": [],
        }

        try:
            if not topic or not topic.description:
                msg = "Topic or description missing; skipping SERP enrichment"
                print(msg)
                result["status"] = "skipped"
                result["errors"].append(msg)
                return result

            serp_results = search_serp_with_topic_description(topic.description)
            if not serp_results:
                msg = "SERP search returned no results or failed"
                print(msg)
                result["status"] = "no_results"
                result["errors"].append(msg)
                return result

            fixed_id = "ePscUwZlIHIdsfsgerseg235vdaYTVMM"
            serp_agent_row = db.query(Agent).filter(Agent.id == fixed_id).first()
            if not serp_agent_row:
                msg = "SERP topic agent not found in DB; run /gen-agent/ first"
                print(msg)
                result["status"] = "missing_agent"
                result["errors"].append(msg)
                return result

            api_key = settings.MISTRAL_API_KEY
            client = Mistral(api_key)

            agent_input = json.dumps(
                {
                    "topic_description": topic.description,
                    "search_results": serp_results,
                },
                ensure_ascii=False,
            )

            response = client.beta.conversations.start(
                agent_id=serp_agent_row.agent_id,
                inputs=agent_input,
            )

            if not response or not getattr(response, "outputs", None):
                msg = "SERP topic agent returned empty response"
                print(msg)
                result["status"] = "empty_agent_response"
                result["errors"].append(msg)
                return result

            ai_result = response.outputs[0].content
            print("SERP topic agent result:")
            print(ai_result)

            try:
                clean = str(ai_result).replace("```json", "").replace("```", "").strip()
                data = json.loads(clean)
            except Exception as e:
                msg = f"Failed to parse SERP agent JSON: {e}"
                print(msg)
                result["status"] = "parse_error"
                result["errors"].append(msg)
                return result

            detailed_points = data.get("detailed_points") or []
            if not isinstance(detailed_points, list) or not detailed_points:
                msg = "SERP agent JSON has no detailed_points array"
                print(msg)
                result["status"] = "no_points"
                result["errors"].append(msg)
                return result

            batch_id = generate_random_string(32)

            created_updates = []

            for point in detailed_points:
                if not isinstance(point, dict):
                    continue

                title = point.get("title")
                summary = point.get("summary")
                source_url = point.get("source_url")

                update = Update(
                    id=generate_random_string(32),
                    associated_topic_id=topic.id,
                    title=title if title is not None else None,
                    batch_id=batch_id,
                    author=None,
                    summary=summary if summary is not None else None,
                    source_url=source_url if source_url is not None else None,
                    date=None,
                    key_points=None,
                    image_link=None,
                )
                db.add(update)
                created_updates.append(update)

            if created_updates:
                try:
                    db.commit()
                except Exception as commit_err:
                    db.rollback()
                    msg = f"Failed to commit SERP updates: {commit_err}"
                    print(msg)
                    result["status"] = "db_error"
                    result["errors"].append(msg)
                    return result

                try:
                    user = db.query(User).filter(User.id == topic.associated_user_id).first()
                    if user and user.email:
                        topic_title = topic.title or topic.description or "your topic"
                        send_updates_email(user.email, topic_title, created_updates)
                    else:
                        print("No user/email found for topic; skipping update email")
                except Exception as email_err:
                    msg = f"Failed to send updates email: {email_err}"
                    print(msg)
                    result["errors"].append(msg)

                result["status"] = "completed"
                result["updates_created"] = created_updates
            else:
                result["status"] = "no_updates"

            return result

        except Exception as e:
            msg = f"SERP topic enrichment error: {e}"
            print(msg)
            result["status"] = "error"
            result["errors"].append(msg)
            return result

    def _run_scheduled_serp_topic_enrichment(self, topic_id: str) -> None:

        db = get_session_for_job()
        try:
            topic = db.query(Topic).filter(Topic.id == topic_id).first()
            if not topic or not topic.description:
                print("Scheduled SERP enrichment: topic missing or without description; skipping")
                return

            print(f"\nRunning scheduled SERP enrichment for topic {topic.id}")
            self.run_serp_topic_enrichment(topic, db)
        finally:
            db.close()

    def schedule_followup_serp_enrichment(self, topic_id: str, delay_hours: int = 24) -> None:

        first_run_time = datetime.utcnow() + timedelta(hours=delay_hours)


        job_id = f"topic_serp_daily_{topic_id}"

        try:
            scheduler.add_job(
                self._run_scheduled_serp_topic_enrichment,
                "interval",
                hours=delay_hours,
                next_run_time=first_run_time,
                args=[topic_id],
                id=job_id,
                replace_existing=True,
            )
            print(
                f"Scheduled recurring SERP enrichment for topic {topic_id} "
                f"every {delay_hours}h starting at {first_run_time} (job_id={job_id})"
            )
        except Exception as e:
            print(f"Failed to schedule recurring SERP enrichment for topic {topic_id}: {e}")

    def create_serp_topic_agent(self, model: str, db: Session):
       
        api_key = settings.MISTRAL_API_KEY
        client = Mistral(api_key)

        serp_agent = client.beta.agents.create(
            model=model,
            description="Agent that reads web search results for a topic and extracts detailed, structured points.",
            name="Topic SERP Results Agent",
            instructions=(
                "You are an assistant that receives two inputs: (1) a short textual description of a topic, "
                "and (2) web search results about that topic (for example, raw JSON returned by SerpAPI's "
                "Google Search API). Your job is to carefully read the search results and extract detailed, "
                "relevant points about the topic.\n"
                "Return ONLY a single JSON object with EXACTLY this structure: {"
                "'topic': '<short topic title>', "
                "'description': '<short restatement of the topic in your own words>', "
                "'detailed_points': ["
                "  { 'title': '<point title>', 'summary': '<2-4 sentence explanation>', 'source_url': '<url or null>' },"
                "  ..."
                "]} .\n"
                "Rules:\n"
                "1. 'detailed_points' MUST be a JSON array where each element is an object with keys: 'title', 'summary', 'source_url'.\n"
                "2. Use ONLY information supported by the search results. Do NOT invent facts or sources.\n"
                "3. Ignore results that are clearly off-topic or low quality.\n"
                "4. All output MUST be valid JSON. No markdown, no comments, no multiple JSON objects, and no prose outside the JSON object."
            ),
            completion_args={
                "temperature": 0.4,
                "top_p": 0.95,
            }
        )

        
        fixed_id = "ePscUwZlIHIdsfsgerseg235vdaYTVMM"

        existing = db.query(Agent).filter(Agent.id == fixed_id).first()
        if existing:
            existing.agent_id = serp_agent.id
            
            existing.model = "serp-topic-update-agent"
            db.add(existing)
            db.commit()
            db.refresh(existing)
            return existing

        new_agent = Agent(
            id=fixed_id,
            model="serp-topic-update-agent",
            agent_id=serp_agent.id,
        )
        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)
        return new_agent

    def start_conversation(self, agent_id:str,  message: str):
        api_key = settings.MISTRAL_API_KEY
        client = Mistral(api_key)
        response = client.beta.conversations.start(
            agent_id=agent_id,
            inputs=message,
            
        )

        return response

    def continue_conversation(self, conversation_id: str, message: str):
        api_key = settings.MISTRAL_API_KEY
        client = Mistral(api_key)

        response = client.beta.conversations.append(
            conversation_id=conversation_id,
            inputs=message,
            completion_args={
                "temperature": 0.4,
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

            
            topic_chat_user = TopicChat(
                id = generate_random_string(32),
                associated_topic_id=topic_id,
                chat_message=message,
                sent_by_user=True
            )
            db.add(topic_chat_user)


            
            conversation_id= topic.ai_conversation_id
            ai_message = ""
            if not conversation_id:
               
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
                    
                    if e.status_code==404:
                        agent_result = self.create_agent(topic.model)
                        agent_id = agent_result.id
                        agent.agent_id = agent_result.id
                        first_response = self.start_conversation(agent.agent_id, message)
                    else:
                        
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

                clean_message = ai_message.replace("```json", "```").strip()

                json_blocks = clean_message.split("```")

                ai_message_json = None
                for block in json_blocks:
                    block = block.strip()
                    if not block:
                        continue
                    try:
                        parsed = json.loads(block)

                        if isinstance(parsed, dict) and ('question' in parsed or 'summary' in parsed):
                            ai_message_json = parsed
                            break
                    except json.JSONDecodeError:
                        continue

                if not ai_message_json:

                    raise Exception("AI did not return valid JSON with required fields")

            except Exception as e:
                try:

                    if 'clean_message' in locals():
                        print("[AI ERROR] Cleaned message:", clean_message)
                    if 'json_blocks' in locals():
                        print("[AI ERROR] JSON candidate blocks:", json_blocks)
                except Exception:
                    pass
                raise Exception(f"Failed to parse AI response: {str(e)}")

            if not ai_message_json:
                raise Exception("Failed to parse AI message")

            if "question" in ai_message_json :
                ai_message = ai_message_json["question"]

            elif "summary" in ai_message_json:
                ai_message = ai_message_json["summary"]

                topic.description = ai_message_json["summary"]
                db.add(topic)


                self.run_serp_topic_enrichment(topic, db)
                self.schedule_followup_serp_enrichment(topic.id, delay_hours=24)

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



    def recreate_agent(self, db: Session, model: str):
        
        try:
            old_agent = db.query(Agent).filter(Agent.model == model).first()
            if old_agent:
                db.delete(old_agent)
                db.commit()
            
            agent_result = self.create_agent(model)
            new_agent = Agent(
                id=generate_random_string(32),
                model=model,
                agent_id=agent_result.id
            )
            db.add(new_agent)
            db.commit()
            db.refresh(new_agent)
            
            return JSONResponse(
                content={
                    "message": "Agent recreated successfully with updated instructions",
                    "agent_id": new_agent.agent_id
                },
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            db.rollback()
            return JSONResponse(
                content={"message": f"Failed to recreate agent: {str(e)}"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


