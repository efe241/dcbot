import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

@pytest.mark.asyncio
async def test_adgem_postback_and_idempotency():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        params = {
            "player_id": "999888777",
            "transaction_id": "adgem_tx_9900",
            "amount": "1.50",
            "campaign_id": "554433",
            "verifier": "test_verifier"
        }
        # First call: credit coins
        res1 = await ac.get("/api/adgem/postback", params=params)
        assert res1.status_code == 200
        assert res1.text == "OK"

        # Second call: duplicate transaction idempotency check
        res2 = await ac.get("/api/adgem/postback", params=params)
        assert res2.status_code == 200
        assert res2.text == "OK"
