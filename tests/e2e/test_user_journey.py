import pytest
from playwright.sync_api import Page, expect
import time

FRONTEND_URL = "http://localhost:3000/query"

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {
            "width": 1280,
            "height": 720,
        }
    }

def test_startup_readiness_gate(page: Page):
    """Verify that the frontend waits for backend readiness."""
    page.goto(FRONTEND_URL)
    
    # Wait for the input field to be visible and enabled
    # We use a longer timeout because the backend might be warming up
    input_box = page.locator('textarea[placeholder*="Ask anything"]')
    input_box.wait_for(state="visible", timeout=30000)
    expect(input_box).to_be_enabled()

def test_simple_factual_query(page: Page):
    """Verify a simple query flows through the entire state machine."""
    page.goto(FRONTEND_URL)
    
    # 1. Wait for ready
    input_box = page.locator('textarea[placeholder*="Ask anything"]')
    input_box.wait_for(state="visible", timeout=30000)
    
    # 2. Submit query
    input_box.fill("What is stochastic gradient descent?")
    page.keyboard.press("Enter")
    
    # 3. Verify state transitions (Visualizer should appear)
    visualizer = page.locator('.pipeline-visualizer')
    expect(visualizer).to_be_visible(timeout=5000)
    
    # 4. Wait for generation to complete (Chat interface should show answer)
    # The generation phase might take up to 20 seconds depending on the model
    answer_block = page.locator('.chat-message-assistant')
    expect(answer_block).to_be_visible(timeout=30000)
    
    # 5. Verify telemetry metrics rendered
    metrics_sidebar = page.locator('.metrics-sidebar')
    expect(metrics_sidebar).to_be_visible()
    expect(metrics_sidebar).to_contain_text("Tokens")
    expect(metrics_sidebar).to_contain_text("Latency")

def test_empty_retrieval_query(page: Page):
    """Verify system handles zero-retrieval gracefully."""
    page.goto(FRONTEND_URL)
    
    input_box = page.locator('textarea[placeholder*="Ask anything"]')
    input_box.wait_for(state="visible", timeout=30000)
    
    # Nonsense query unlikely to retrieve chunks
    input_box.fill("zzxqywvkasdf1234987 nonsense word")
    page.keyboard.press("Enter")
    
    # Wait for completion
    answer_block = page.locator('.chat-message-assistant')
    expect(answer_block).to_be_visible(timeout=30000)
    
    # Verify no context was retrieved (Intelligence View should indicate 0)
    intelligence_view = page.locator('.retrieval-intelligence-view')
    # If the intelligence view is open or opens automatically on context
    # If no context, it might say "0 sources"
    # Actually, we can check the metrics sidebar for "0 chunks"
    metrics_sidebar = page.locator('.metrics-sidebar')
    expect(metrics_sidebar).to_contain_text("0 Chunks")

def test_trust_verification_rendering(page: Page):
    """Verify the Trust Score is displayed after generation."""
    page.goto(FRONTEND_URL)
    
    input_box = page.locator('textarea[placeholder*="Ask anything"]')
    input_box.wait_for(state="visible", timeout=30000)
    
    input_box.fill("Explain attention mechanisms in transformers.")
    page.keyboard.press("Enter")
    
    # Wait for completion and trust verification
    # Trust verification is the final phase
    trust_score = page.locator('text=Trust Score')
    expect(trust_score).to_be_visible(timeout=45000)

def test_request_id_telemetry(page: Page):
    """Verify request IDs are bound to the session."""
    page.goto(FRONTEND_URL)
    
    input_box = page.locator('textarea[placeholder*="Ask anything"]')
    input_box.wait_for(state="visible", timeout=30000)
    
    input_box.fill("Short query.")
    page.keyboard.press("Enter")
    
    expect(page.locator('.chat-message-assistant')).to_be_visible(timeout=30000)
    
    # Request ID should be in the developer panel or metrics
    dev_panel = page.locator('text=Request ID')
    expect(dev_panel).to_be_visible()
