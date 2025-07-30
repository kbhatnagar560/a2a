import asyncio
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright
from groq import Groq

class VerizonPlanAgent:
    def __init__(self, groq_api_key: str = None):
        if groq_api_key:
            self.groq_client = Groq(api_key=groq_api_key)
        else:
            # You might want to load from environment variable
            self.groq_client = Groq(api_key="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")
        self.plans = []

    async def scrape_plans(self):
        """Use Playwright to scrape plans"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            
            try:
                print(" Scraping Verizon Unlimited plans...")
                await page.goto("https://www.verizon.com/plans/unlimited", timeout=30000)
                await page.wait_for_timeout(3000)
                
                # Find plan cards
                plan_cards = page.locator('.plan[data-plan]')
                count = await plan_cards.count()
                print(f" Found {count} plan cards")
                
                plans = []
                for i in range(count):
                    card = plan_cards.nth(i)
                    
                    # Get plan name
                    try:
                        h3 = card.locator('h3')
                        name = await h3.inner_text()
                        print(f"Debug: Retrieved inner text is: '{name}'")
                        name = " ".join(name.split()).strip() if name else "Unknown Plan"
                
                    except Exception as e:
                        print(f"   Error getting plan name: {e}")
                        name = "Unknown Plan"
                    
                    # Get price directly from element
                    try:
                        price_element = card.locator('[data-plan-price-value="full"]')
                        price_text = await price_element.inner_text()
                        price = float(price_text.replace('$', '').replace('/mo', '').strip())
                    except Exception as e:
                        print(f"   Error getting price: {e}")
                        price = 0
                    
                    # Get features
                    try:
                        feature_elements = card.locator('.feature__title')
                        features = await feature_elements.all_inner_texts() if feature_elements else []
                        features = [feature.strip() for feature in features]
                    except Exception as e:
                        print(f"   Error getting features: {e}")
                        features = []
                    
                    
                    plans.append({
                        "name": name,
                        "price": price,
                        "features": features
                    })
                    print(f"   {name} - ${price}")
                
                self.plans = plans
                return plans
                
            except Exception as e:
                print(f"Error during scraping: {e}")
                return []
            finally:
                await browser.close()

    def get_recommendation(self, user_input: str) -> str:
        """Use AI to recommend best plan based on user needs."""
        # Attempt to load plans from JSON. Scrape only if loading fails.
        if not self.load_plans() and not self.plans:
            print("Scraping plans as no JSON data is available...")
            asyncio.run(self.scrape_plans())
            self.save_plans()

        if not self.plans:
            return "No plans available. Could not retrieve any plan data."

        plans_text = ""
        for plan in self.plans:
            features_text = ', '.join(plan['features'][:3]) if plan['features'] else 'No features listed'
            plans_text += f"\n{plan['name']}: ${plan['price']}/month\nFeatures: {features_text}\n"
        
        prompt = f"""
        User said: "{user_input}"
        
        Available Verizon plans:
        {plans_text}
        
        Based on the user's needs, recommend the BEST plan and explain why in 2-3 sentences.
        Be conversational and helpful.
        """
        
        try:
            response = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error getting AI recommendation: {e}")
            return "Sorry, I couldn't process your request. Please try again."
    
    def save_plans(self, filename: str = "verizon_plans.json"):
        """Save scraped plans to JSON"""
        base_dir = os.path.dirname(__file__)  
        file_path = os.path.join(base_dir, filename)
        data = {
            "extracted_at": datetime.now().isoformat(),
            "total_plans": len(self.plans),
            "plans": self.plans
        }
        
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            print(f" Saved {len(self.plans)} plans to {file_path}")
        except Exception as e:
            print(f" Error saving plans: {e}")

    def load_plans(self, filename: str = "verizon_plans.json"):
        """Load plans from a JSON file located in the same directory."""
        current_directory = os.path.abspath(os.path.dirname(__file__))
        file_path = os.path.join(current_directory, filename)

        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    self.plans = data.get("plans", [])
                    print(f"Loaded {len(self.plans)} unlimited plans from {file_path}")
                    return True
            except Exception as e:
                print(f"Error loading plans: {e}")
        return False

# CLI interface for standalone usage
async def main():
    """Main function for CLI usage"""
    agent = VerizonPlanAgent()
    
    if not agent.load_plans() or not agent.plans:
        print("No JSON data available or loaded plans are empty. Scraping plans...")
        plans = await agent.scrape_plans()
        
        if not plans:
            print(" No plans were scraped. Please check the website structure.")
            return
        
        agent.save_plans()
    
    
    
    # Step 2: Interactive recommendations with AI
    print("\n Plan Recommendation Assistant")
    print("=" * 40)
    
    while True:
        user_input = input("\n What are you looking for in a plan? (or 'quit' to exit): ")
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print(" Goodbye!")
            break
        
        if user_input.strip():
            print("\n Let me think...")
            recommendation = agent.get_recommendation(user_input)
            print(f"\n {recommendation}")
        else:
            print("Please enter a valid request.")


if __name__ == "__main__":
    print("Running Verizon Unlimited Plan Agent in CLI mode...")
    asyncio.run(main())
