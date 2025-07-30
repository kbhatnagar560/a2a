from typing import Dict, Any
import uvicorn

# a2a imports (official a2a-sdk)
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.utils import new_agent_text_message

# Import our core agent
from plan_agent import VerizonPlanAgent


class VerizonPlanAgentExecutor(AgentExecutor):
    """a2a executor that wraps the VerizonPlanAgent"""
    
    def __init__(self, groq_api_key: str = None):
        super().__init__()
        self.verizon_agent = VerizonPlanAgent(groq_api_key)
        self._plans_loaded = False

    async def _ensure_plans_loaded(self):
        """Ensure plans are scraped before making recommendations"""
        if not self._plans_loaded:
            print(" Loading Verizon plans...")
            await self.verizon_agent.scrape_plans()
            self._plans_loaded = True

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the agent request - REQUIRED abstract method implementation"""
        try:
            # Get user input from context
            user_input = context.get_user_input()
            print(f" Received user input: {user_input}")
            
            # Ensure plans are loaded
            await self._ensure_plans_loaded()
            
            if not user_input or not user_input.strip():
                response_text = "Please provide your phone plan needs (e.g., 'I need unlimited data for streaming')"
            else:
                # Get recommendation from our agent
                recommendation = self.verizon_agent.get_recommendation(user_input)
                response_text = f" Plan Recommendation:\n\n{recommendation}\n\n📊 Based on {len(self.verizon_agent.plans)} available plans"
            
            # Send response back through event queue
            message = new_agent_text_message(response_text)
            event_queue.enqueue_event(message)
            print(f"Response sent: {response_text[:100]}...")
            
        except Exception as e:
            error_message = f" Error processing request: {str(e)}"
            print(error_message)
            event_queue.enqueue_event(new_agent_text_message(error_message))
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handle cancellation requests - REQUIRED abstract method implementation"""
        print(" Cancellation requested but not supported")
        raise Exception('Cancellation not supported for Verizon Plan Agent')


def create_agent_skills():
    """Define the skills this agent can perform"""
    
    recommend_skill = AgentSkill(
        id='recommend_plan',
        name='Recommend Verizon Plan',
        description='Recommends the best Verizon plan based on user needs by scraping current plans and using AI',
        tags=['verizon', 'plans', 'recommendation', 'ai', 'scraping'],
        examples=[
            'I need unlimited data and hotspot',
            'What plan is best for a family of 4?',
            'I want the cheapest plan with 5G',
            'Best plan for streaming videos?',
            'I need a plan with international calling'
        ],
    )
    
    return [recommend_skill]


def create_agent_card(skills):
    """Create the agent card that describes this agent's capabilities"""
    
    return AgentCard(
        name='Verizon Plan Assistant',
        description='AI agent that scrapes current Verizon unlimited plans and provides personalized recommendations based on your needs',
        url='http://localhost:8000/',
        version='1.0.0',
        defaultInputModes=['text'],
        defaultOutputModes=['text'],
        capabilities=AgentCapabilities(streaming=False),
        skills=skills,
    )


def create_a2a_server(groq_api_key: str = None, host: str = "0.0.0.0", port: int = 8000):
    """Create and configure the a2a agent server"""
    
    print(" Creating A2A server components...")
    
    # Create skills and agent card
    skills = create_agent_skills()
    agent_card = create_agent_card(skills)
    print(f" Agent card created with {len(skills)} skills")
    
    # Create the agent executor
    agent_executor = VerizonPlanAgentExecutor(groq_api_key)
    print(" Agent executor created")
    
    # Create the request handler with your executor
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=InMemoryTaskStore(),
    )
    print(" Request handler created")
    
    # Create the a2a server
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    print(" A2A server application created")
    
    return server, host, port


def main():
    """Main function to run the a2a server"""
    print(" Starting Verizon Plan Assistant A2A Server")
    print("=" * 50)
    print(" Server will be available at: http://localhost:8000")
    print(" Agent card endpoint: http://localhost:8000/.well-known/agent.json")
    print(" Tasks endpoint: http://localhost:8000/")
    print("=" * 50)
    
    try:
        server, host, port = create_a2a_server()
        print(f" Server setup complete! Starting on {host}:{port}")
        uvicorn.run(server.build(), host=host, port=port)
    except Exception as e:
        print(f" Failed to start server: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()