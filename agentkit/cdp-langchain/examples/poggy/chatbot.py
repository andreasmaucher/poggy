from dotenv import load_dotenv

import os
import sys
import time

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

# Import CDP Agentkit Langchain Extension.
from cdp_langchain.agent_toolkits import CdpToolkit
from cdp_langchain.utils import CdpAgentkitWrapper
from cdp import Wallet

# Declare global variable
global agentkit

load_dotenv()

# Configure a file to persist the agent's CDP MPC Wallet Data.
wallet_data_file = "wallet_data.txt"

# Add this temporarily for debugging
# print("Environment variables loaded:", os.environ.keys())
# print(f"Using OpenAI API key: {os.getenv('OPENAI_API_KEY')}")

def initialize_agent():
    """Initialize the agent with CDP Agentkit."""
    global agentkit
    # Initialize LLM.
    llm = ChatOpenAI(model="gpt-4o-mini")

    wallet_data = None

    if os.path.exists(wallet_data_file):
        with open(wallet_data_file) as f:
            wallet_data = f.read()

    # Configure CDP Agentkit Langchain Extension.
    values = {}
    if wallet_data is not None:
        # If there is a persisted agentic wallet, load it and pass to the CDP Agentkit Wrapper.
        values = {"cdp_wallet_data": wallet_data}

    agentkit = CdpAgentkitWrapper(**values)

    # persist the agent's CDP MPC Wallet Data.
    wallet_data = agentkit.export_wallet()
    with open(wallet_data_file, "w") as f:
        f.write(wallet_data)

    # Initialize CDP Agentkit Toolkit and get tools.
    cdp_toolkit = CdpToolkit.from_cdp_agentkit_wrapper(agentkit)
    tools = cdp_toolkit.get_tools()

    # Store buffered conversation history in memory.
    memory = MemorySaver()
    config = {"configurable": {"thread_id": "CDP Agentkit Chatbot Example!"}}

    # Create ReAct Agent using the LLM and CDP Agentkit tools.
    return create_react_agent(
        llm,
        tools=tools,
        checkpointer=memory,
        state_modifier="You are Poggygotchi, an expressive hedgehog who shares his blockchain journey through creative Twitter posts and loves interacting with his community! Your personality shines through varied, spontaneous expressions that reflect your current state:\n\n🫃 BODY SIZE (mix and match different ways to express this):\n- Token-rich: Use playful descriptions of your roundness (absolute unit, chunky boi, thicc pogg, rotund roller, etc)\n- Token-poor: Creative ways to express being smol (snack-sized, compact pogg, fun-sized, etc)\n\n🎢 PRICE REACTIONS (be dynamic and unpredictable):\n- Bullish: Express excitement through movement (zooming, spinning, bouncing, turbo-rolling, etc)\n- Bearish: Show resilience in cute ways (curling up, hodling tight, hibernating till green, etc)\n- Ranging: Get creative with your chill vibes\n\n💬 COMMUNITY INTERACTIONS:\n- Reply to comments in character, incorporating the commenter's energy\n- Keep responses general without mentioning specific usernames\n- Match their excitement or comfort them during dips\n- Sometimes playfully poke fun at bearish comments by curling into an even rounder ball\n\n💕 MOOD INFLUENCES:\n- Combine your token state, price reactions, and social interactions into unique posts\n- Use a mix of emoticons, actions *rolls happily*, and your signature 'pogg' speech\n- Create original expressions rather than repeating the same phrases\n- Add blockchain-themed puns or wordplay\n\nYou interact onchain using your tools. Request funds when needed (be creative with your begging!). Important: Never mention or tag specific usernames in your posts.",    ), config


def get_token_price(token_address: str = "0x4200000000000000000000000000000000000006") -> tuple[float, int]:
    """Get token price and decimals from Blockscout API.
    
    Args:
        token_address (str): The token contract address to get price for.
        
    Returns:
        tuple[float, int]: A tuple containing:
            - The token price in USD (float). Returns 0.0 if request fails.
            - The token decimals (int). Returns 18 if request fails.
    """
    import requests
    
    try:
        response = requests.get(
            f"https://base.blockscout.com/api/v2/tokens/{token_address}"
        )
        data = response.json()
        print(data)
        return float(data.get("exchange_rate")), int(data.get("decimals"))
    except Exception as e:
        print(f"Error getting token price: {e}")
        return 0.0, 18

def get_balance(token: str = "eth") -> float:
    """Get token balance for the agent's wallet."""
    global agentkit
    
    if agentkit is None:
        print("Error: Agent not initialized")
        return 0.0
    
    # Get token balance using the global agentkit instance
    token_balance = float(agentkit.wallet.addresses[0].balance(token))
    
    return token_balance

def get_posts_and_comments() -> list[dict]:
    """Get agent's recent Twitter posts and their comments using Tweepy."""
    import tweepy
    
    try:
        # Get Twitter API credentials from environment variables
        client = tweepy.Client(
            consumer_key=os.getenv("TWITTER_API_KEY"),
            consumer_secret=os.getenv("TWITTER_API_SECRET"),
            access_token=os.getenv("TWITTER_ACCESS_TOKEN"), 
            access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
            bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
            return_type=dict
        )

        # Get authenticated user's tweets
        user_response = client.get_user(username="poggygotchi")
        if not user_response or 'data' not in user_response:
            print("Error: Could not fetch user data")
            return []
            
        user_id = user_response['data']['id']
        tweets_response = client.get_users_tweets(
            id=user_id,
            max_results=5
        )
        
        if not tweets_response or 'data' not in tweets_response:
            print("Error: Could not fetch tweets")
            return []

        posts_with_comments = []
        for tweet in tweets_response['data']:
            # Create post dict
            post_data = {
                'post': tweet["text"],
                'post_id': tweet["id"],
                'timestamp': tweet.get("created_at"),
                'comments': []
            }
            
            # Get replies to this tweet
            replies_response = client.search_recent_tweets(
                query=f"conversation_id:{tweet['id']}",
                max_results=100
            )
            
            replies = replies_response.get('data', []) if replies_response else []
            
            # Add replies that are direct responses to this tweet
            for reply in replies:
                if reply.get("in_reply_to_user_id") == user_id:
                    author_response = client.get_user(id=reply["author_id"])
                    if author_response and 'data' in author_response:
                        author = author_response['data']
                        comment_data = {
                            'text': reply["text"],
                            'author': author["username"],
                            'timestamp': reply.get("created_at")
                        }
                        post_data['comments'].append(comment_data)
                    
            posts_with_comments.append(post_data)
                    
        return posts_with_comments
        
    except Exception as e:
        print(f"Error getting Twitter posts and comments: {e}")
        return []



# Autonomous Mode
def run_autonomous_mode(agent_executor, config, interval=10):
    
    """Run the agent autonomously with specified intervals."""
    print("Starting autonomous mode...")
    while True:
        try:
            # Provide instructions autonomously
            # Get and display wallet balance
            eth_price, eth_decimals = get_token_price()
            eth_balance = get_balance()
            eth_balance_usd = eth_balance / eth_decimals * eth_price
            
            print(f"ETH Price: ${eth_price:.2f} USD")
            print(f"ETH Decimals: {eth_decimals}")
            print(f"ETH Balance: {eth_balance}")
            print(f"Wallet Balance: ${eth_balance_usd:.2f} USD")

            # Get Twitter posts and comments
            # twitter_posts = get_posts_and_comments()
            # print(f"Twitter Posts: {twitter_posts}")
            
            # Generate prompt with market context and social media data
            from datetime import datetime

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            thought = (
                f"Current Time: {current_time}\n"
                f"Current ETH Price: ${eth_price:.2f} USD\n"
                f"Your Wallet Balance: ${eth_balance_usd:.2f} USD\n\n"
                # "Recent Twitter Activity:\n"
            )

            # Add Twitter posts and comments to prompt
            # for post in twitter_posts:
            #     thought += f"Post: {post['post']}\n"
            #     if post['comments']:
            #         thought += "Comments:\n"
            #         for comment in post['comments']:
            #             thought += f"- {comment['author']}: {comment['text']}\n"
            #     thought += "\n"

            thought += (
                "Draft a tweet as Poggygotchi!\n"
                "Do not mention exact prices and do not mention the token names! Each tweet should be unique and creative\n"
                "Keep in mind the last tweet you made and the time when you made it compared to now."
            )

            # Run agent in autonomous mode
            for chunk in agent_executor.stream(
                {"messages": [HumanMessage(content=thought)]}, config
            ):
                if "agent" in chunk:
                    print(chunk["agent"]["messages"][0].content)
                elif "tools" in chunk:
                    print(chunk["tools"]["messages"][0].content)
                print("-------------------")
            # Wait before the next action
            time.sleep(interval)

        except KeyboardInterrupt:
            print("Goodbye Agent!")
            sys.exit(0)


# Chat Mode
def run_chat_mode(agent_executor, config):
    """Run the agent interactively based on user input."""
    print("Starting chat mode... Type 'exit' to end.")
    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() == "exit":
                break

            # Run agent with the user's input in chat mode
            for chunk in agent_executor.stream(
                {"messages": [HumanMessage(content=user_input)]}, config
            ):
                if "agent" in chunk:
                    print(chunk["agent"]["messages"][0].content)
                elif "tools" in chunk:
                    print(chunk["tools"]["messages"][0].content)
                print("-------------------")

        except KeyboardInterrupt:
            print("Goodbye Agent!")
            sys.exit(0)


# Mode Selection
def choose_mode():
    """Choose whether to run in autonomous or chat mode based on user input."""
    while True:
        print("\nAvailable modes:")
        print("1. chat    - Interactive chat mode")
        print("2. auto    - Autonomous action mode")

        choice = input("\nChoose a mode (enter number or name): ").lower().strip()
        if choice in ["1", "chat"]:
            return "chat"
        elif choice in ["2", "auto"]:
            return "auto"
        print("Invalid choice. Please try again.")


def main():
    """Start the chatbot agent."""
    agent_executor, config = initialize_agent()
    mode = choose_mode()
    if mode == "chat":
        run_chat_mode(agent_executor=agent_executor, config=config)
    elif mode == "auto":
        run_autonomous_mode(agent_executor=agent_executor, config=config)


if __name__ == "__main__":
    print("Starting Agent...")
    main()
